dcron
=====

Run tasks on containers using labels.

Normally you would use some implementation of cron for this. But having the crontab somewhere on your host instead of alongside your containers is not very friendly. And most cron implementations do not work very well in containers. On the other hand the definition of jobs in crontab is elegant. So this implementation combines the elegancy of cron with labels on containers to achieve some kind of "crontab for containers".

Usage
-----

Just add the following labels to your docker-compose file.

.. code-block:: yaml

    version: "3.8"
    name: "my-cool-project"

    services:
        hello:
            image: hello-world:latest
        labels:
            - "dcron.jobs.hello.rule=@hourly"
            - "dcron.jobs.hello.execute=echo 'test'"
        
        dcron:
            image: dcron:latest
            volumes:
                - "/var/run/docker.sock:/var/run/docker.sock:ro"

Note that `dcron` needs access to the Docker API to parse the labels.

Thanks to
---------

- `py-docker` for the Python Docker API
- `croniter` for parsing cron-like rules