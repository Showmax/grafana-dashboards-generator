#! /usr/bin/env python
"""
"""

from __future__ import unicode_literals

import os
import sys
import logging
import argparse
import json

import yaml

PROJ_ROOT = os.path.dirname(sys.argv[0])
OUTPUT_DIR = os.path.join(PROJ_ROOT, 'dashboards')
CONFIG_FILE = os.path.join(PROJ_ROOT, 'config.yml')


class ConfigObject(object):
    inherits = None

    def __init__(s, name, init_dict):
        s.__dict__.update(init_dict)
        s.name = name

    def __unicode__(s):
        return unicode(s.__dict__)

    def converge(s, others):
        """converge templates

        if ConfigObject has an inherits 'variable', fill in values from it.
        others == all ConfigObject's type instances from configfile (e.g. for
        converging dashboard templates, all dashboards found in config file

        convergence is recursive ("template might use "inherits" variable
        itself)

        inherited attribute is set to inherits, and inherits is set to None, to
        show, that template has already been instantiated and inherited
        attribute keeps the original template name for other purposes

        BEWARE OF LOOPS :-)
        """
        if s.inherits is not None:
            data = others[s.inherits].converge(others)
            data.__dict__.update(s.__dict__)
            data.inherited = data.inherits
            data.inherits = None
            return data

        return s.__class__(s.name, s.__dict__)

    def fill(s, attr, others):
        """fill in attribute

        e.g. attr == 'rows', other == all rows in config file,
        items in s.rows attribute gets replaced with appropriate objects
        from others instantiating teplates on the way
        """

        fill_list = []
        for a in getattr(s, attr):
            fill_list.append(others[a].converge(others))

        result = s.__class__(s.name, s.__dict__)
        setattr(result, attr, fill_list)

        return result

    def generate(s, context):
        result = {}

        for i in s.copy_items:
            result[i] = getattr(s, i)

        if hasattr(s, 'optional_copy_items'):
            for i in s.optional_copy_items:
                try:
                    result[i] = getattr(s, i)
                except AttributeError:
                    continue

        return result


class Dashboard(ConfigObject):
    copy_items = (
        'editable',
        'hideControls',
        'originalTitle',
        'refresh',
        'sharedCrosshair',
        'style',
        'tags',
        'timezone',
        'title',
    )
    optional_copy_items = ('folder',)

    instantiate = True
    title = 'Unnamed'
    originalTitle = 'Unnamed'

    tags = []
    rows = []
    dashboardLinks = []
    templating = []

    def generate(s, context):
        """TODO: I should check, that there are no "unused" items in the config
        (that would probably be a typo)
        """

        result = super(Dashboard, s).generate(context)

        result['rows'] = [row.generate(context, s) for row in s.rows]

        result['links'] = [link.generate(context) for link in s.dashboardLinks]

        result['time'] = {
            'from': s.time['from'],
            'to': s.time['to'],
        }

        result['timepicker'] = {
            'now': s.now,
            'refresh_intervals': s.refresh_intervals,
            'time_options': s.time_options,
        }

        result['templating'] = {
            'list': [
                template.generate(context, s) for template in s.templating],
        }

        result['annotations'] = {
            'list': [],
        }

        result['schemaVersion'] = 7
        result['version'] = 22

        return result


class Row(ConfigObject):
    """TODO: check type: matches with definition to avoid certain hard to find
    errors in config file

    also inheritance will inherit different types :-/

    etc...

    FIXME: I presume row == panel
    """

    _last_id = 0

    seriesOverrides = []
    aliasColors = {}

    copy_items = (
        'collapse',
        'editable',
        'height',
    )
    legend_items = (
        'legend_alignAsTable',
        'legend_avg',
        'legend_current',
        'legend_max',
        'legend_min',
        'legend_show',
        'legend_total',
        'legend_values',
    )
    grid_items = (
        'grid_leftLogBase',
        'grid_leftMax',
        'grid_leftMin',
        'grid_rightLogBase',
        'grid_rightMax',
        'grid_rightMin',
        'grid_threshold1',
        'grid_threshold1Color',
        'grid_threshold2',
        'grid_threshold2Color',
    )
    panel_copy_items = (
        'aliasColors',
        'bars',
        'datasource',
        'editable',
        'error',
        'fill',
        'leftYAxisLabel',
        'lines',
        'lineWidth',
        'nullPointMode',
        'percentage',
        'pointradius',
        'points',
        'renderer',
        'rightYAxisLabel',
        'seriesOverrides',
        'span',
        'stack',
        'steppedLine',
        'timeFrom',
        'title',
        'type',
    )

    @classmethod
    def gen_id(cls):
        cls._last_id += 1
        return cls._last_id

    def generate(s, context, parent_dashboard):
        result = super(Row, s).generate(context)

        result['title'] = 'Row'
        result['showTitle'] = False

        panel = {}

        for item in s.panel_copy_items:
            panel[item] = getattr(s, item)

        panel['id'] = Row.gen_id()
        panel['links'] = []
        panel['timeShift'] = None
        panel['tooltip'] = {
            'shared': s.tooltip_shared,
            'value_type': 'cumulative'}
        panel['y_formats'] = s.y_formats

        panel['legend'] = {}
        lss = len('legend_')
        for li in s.legend_items:
            panel['legend'][li[lss:]] = getattr(s, li)

        panel['grid'] = {}
        gss = len('grid_')
        for gi in s.grid_items:
            panel['grid'][gi[gss:]] = getattr(s, gi)

        # targets - a.k.a. graphs/expressions in a single row
        assert len(s.targets) <= 26  # refId is a single letter (AFAIK)
        panel['targets'] = []
        target_cnt = 0
        for target_data in s.targets:
            target = {}
            if 'legend_format' in target_data:
                target['legendFormat'] = target_data['legend_format']
            else:
                target['legendFormat'] = s.legend_format
            if 'intervalFactor' in target_data:
                target['intervalFactor'] = target_data['intervalFactor']
            else:
                target['intervalFactor'] = s.intervalFactor
            target['refId'] = chr(ord('A') + target_cnt)
            try:
                target['expr'] = target_data['expression'] % \
                    parent_dashboard.expvars
            except KeyError:
                print >>sys.stderr, "missing variable while trying to " \
                                    "fill expr: %s" % target_data['expression']
                print >>sys.stderr, "for dashboard %s" % parent_dashboard.title
                sys.exit(1)
            # workaround for double-\ in expressions
            target['expr'] = target['expr'].replace('\\', '\\\\')
            panel['targets'].append(target)
            target_cnt += 1

        result['panels'] = [panel]

        return result


class Template(ConfigObject):
    copy_items = (
        'datasource',
        'allValue',
        'current',
        'hide',
        'includeAll',
        'label',
        'multi',
        'options',
        'refresh',
        'sort',
        'tagValuesQuery',
        'tags',
        'tagsQuery',
        'type',
        'useTags',
    )

    def generate(s, context, parent_dashboard):
        result = super(Template, s).generate(context)

        # Set template name and query.
        result['name'] = s.name
        result['query'] = 'label_values(%s, %s)' % (s.metric, s.label)

        # This allows restricting values of the template by a regexp.
        #
        # When `templating_regexps` dict is defined on a dashboard and contains
        # a key with the same name as the name of the template, use a regexp
        # defined as an expvar with the same name as the value of the key.
        # This allows overriding the regexp per dashboard.
        if hasattr(parent_dashboard, 'templating_regexps') and \
                s.name in parent_dashboard.templating_regexps:
            result['regex'] = parent_dashboard.expvars[
                parent_dashboard.templating_regexps[s.name]]

        return result


class DashboardLink(ConfigObject):
    copy_items = ('icon', 'tags', 'targetBlank', 'type', 'url', 'title')

    def generate(s, context):
        return super(DashboardLink, s).generate(context)


class YamlConfigParser(object):
    dashboards = {}
    graphs = {}
    rows = {}
    templating = {}
    dashboardLinks = {}

    def __init__(s, config_file='./config.yml'):
        s.config_file = config_file
        logging.debug("YamlConfigParser: reading %s" % s.config_file)
        with open(s.config_file, 'r') as f:
            s.yaml = yaml.load(f)

    def parse(s):
        logging.debug("YamlConfigParser: parsing")

        top_level_items = (
            ('dashboards', Dashboard, s.dashboards),
            ('rows', Row, s.rows),
            ('templating', Template, s.templating),
            ('dashboardLinks', DashboardLink, s.dashboardLinks),
        )

        for name, class_, store in top_level_items:
            for item in s.yaml[name]:
                store[item] = class_(item, s.yaml[name][item])

        for dash in s.dashboards:
            # FIXME: not nice
            logging.debug("templatization & filling of %s dashboard" % dash)
            s.dashboards[dash] = s.dashboards[dash].converge(s.dashboards)
            # order of template instantiation and filling is not held (yaml
            # returns dicts even if they are ordered in config file), sometimes
            # we receive an already "filled" instance of dashboard when
            # inherited, check for that eventuality and skip fill() in that
            # case
            if len(s.dashboards[dash].rows) and \
                    not isinstance(s.dashboards[dash].rows[0], ConfigObject):
                s.dashboards[dash] = s.dashboards[dash].fill('rows', s.rows)
            if len(s.dashboards[dash].templating) and \
                    not isinstance(s.dashboards[dash].templating[0], Template):
                s.dashboards[dash] = s.dashboards[dash].fill(
                    'templating', s.templating)
            if len(s.dashboards[dash].dashboardLinks) and \
                    not isinstance(
                        s.dashboards[dash].dashboardLinks[0],
                        ConfigObject):
                s.dashboards[dash] = s.dashboards[dash].fill(
                    'dashboardLinks', s.dashboardLinks)


class DashboardGenerator(object):
    def __init__(s, ycp):
        s.ycp = ycp

    def __iter__(s):
        for dash_name, dash in s.ycp.dashboards.iteritems():
            if dash.instantiate:
                yield [dash_name] + s.gen_dashboard(dash)

    def gen_dashboard(s, d):
        dash_dict = d.generate(s.ycp.dashboards)
        dash_folder = dash_dict.pop('folder', 'no_folder')  # default folder
        return [dash_folder, json.dumps(dash_dict)]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose',
                        dest='verbose', action='store_true',
                        help='be a lil bit verbose')
    parser.add_argument('-c', '--config-file',
                        dest='config_file',
                        default=CONFIG_FILE)
    parser.add_argument('-d', '--dest-dir',
                        dest='dest_dir',
                        default=OUTPUT_DIR)
    parser.add_argument('-n', '--noop',
                        dest='noop', action='store_true',
                        help="don't create json dashboard files")
    return parser.parse_args()


def main():
    logging.basicConfig(stream=sys.stderr)
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.ERROR)

    ycp = YamlConfigParser(config_file=args.config_file)
    ycp.parse()
    dg = DashboardGenerator(ycp)

    if not args.noop:
        logging.debug('writing %s' % os.path.join(args.dest_dir, 'index'))
        index_f = open(os.path.join(args.dest_dir, 'index'), 'w')
    else:
        logging.debug('would be writing %s' %
                      os.path.join(args.dest_dir, 'index'))

    for dashboard_name, dashboard_folder, dashboard in dg:
        out_fn = os.path.join(args.dest_dir,
                              dashboard_folder,
                              '%s.json' % dashboard_name)
        if args.noop:
            logging.debug('would be writing %s' % out_fn)
        else:
            logging.debug('writing %s' % out_fn)
            if dashboard_folder and not os.path.exists(os.path.dirname(out_fn)):
                os.makedirs(os.path.dirname(out_fn))
            with open(out_fn, 'w') as f:
                print >>f, dashboard
                print >>index_f, os.path.join(dashboard_folder,
                                              '%s.json' % dashboard_name)


if __name__ == '__main__':
    main()
