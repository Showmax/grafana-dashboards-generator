# Grafana dashboards generator

We use this project at [ShowMax](http://tech.showmax.com) to generate JSON definitions of Grafana dashboards. Main motivation for the existence of this tool is to

  * have a central place for keeping all dashboards in human readable code
  * track changes with git
  * be able to deploy dashboards to [Grafana](http://grafana.org) started in fresh container without need for persisting changes made into the container.

We use the awesome [Prometheus](http://www.prometheus.io) for storing our metrics.

## Using the generator

We are using the generator as a git submodule in our projects, which hold the actual configuration files. The typical configuration project contains:

  - ``config.yml`` with dashboards definition
  - ``Makefile`` for generating configuration and deploying generated dashboards to Grafana

Then the day-to-day use looks like:

  1. edit ``config.yml``
  1. run ``make genconfig``
  1. if everything is happy, commit updated ``config.yml`` to git
  1. run ``git push``
  1. run ``make deploy``

### Preparing configuration project

To start using `grafana-dashboards-generator` you should create a new git repository for holding your configuration. The process of starting a new project would look something like

```bash
mkdir company-awesome-dashboards && cd company-awesome-dashboards
git init
git submodule add git@github.com:ShowMax/grafana-dashboards-generator.git
cp grafana-dashboards-generator/Makefile.example Makefile
cp grafana-dashboards-generator/config.yml.example config.yml
```

You are now ready to edit ``Makefile`` to configure your ``deploy`` target. As well as edit ``config.yml`` to configure your awesome dashboards.

### Deploying to Grafana

We have omitted deploy step from the `Makefile` as it will be environment specific. In general you need to POST generated files (which are located in `dashboards` directory) to Grafana. We have the following configuration in our Grafana `Dockerfile`:

```bash
export GF_DASHBOARDS_JSON_ENABLED=true
export GF_DASHBOARDS_JSON_PATH=/opt/showmax/grafana-dashboards/dashboards
```

And then just restart Grafana, so it reads new configuration.

## TODO

List of things we would like to do see in the future versions:

  * error reporting if invalid configuration is passed, stack traces are useless
  * graph_overrides to dashboard section and maybe something similar to `seriesOverride` as well
```
       graph_overrides:
           height: 500px
       will "inject" height for all graphs in this dashboard regardless of
           graph template
```
  * `expvars` - allow list and instantiate expression for all values
  * better inheritance of dashboard sections - inherit all rows and change/discard just few of them, inherit all expvars and override/discard just some of them, ditto for tags
