# EVCommunities demo starter

Quick instructions:

1. Create `.env` file based on `.env.template` file and edit the settings.
2. Edit the settings for the simulation platform on files `configuration/common.env`, `configuration/mongodb.env` and `configuration/rabbitmq.env`.
3. If there is a need, edit the sources of component manifest files on `configuration/components.yml`.
4. If there is a need, edit the required Docker image names on `configuration/docker_images.txt`.
5. Start the web server for the simulation starter:

    ```bash
    docker-compose up --detach
    ```

6. The web server is started at address `http://localhost:8500` and the API documentation can be accessed at `http://localhost:8500/docs`. The port number might be different depending on the setting at `.env`.
