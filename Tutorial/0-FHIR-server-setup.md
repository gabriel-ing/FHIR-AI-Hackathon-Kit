# Setting up IRIS-Health with a FHIR server

In this tutorial, we will be using an instance of IRIS-health with a FHIR server, from within a docker container. There are lots of good tutorials on how to use [IRIS-community editions with docker](https://community.intersystems.com/post/running-intersystems-iris-docker-step-step-guide-part-1-basics-custom-dockerfile), but for now I am going to use a pre-loaded build. This repository includes a docker template forked from [IRIS-health + FHIR docker starter repo](https://github.com/pjamiesointersystems/Dockerfhir/tree/main). The template supplied here has minor changes (different ports published), but are functionally the same. 

If you would rather set up a FHIR server from scratch with a clean edition of IRIS-health-community, there is a tutorial to [Create a FHIR Server in 5 minutes](../Additional-demos/CreateAFHIRServerIn5Minutes.md).

To start, clone this repository: 

	git clone https://github.com/intersystems-community/FHIR-AI-Hackathon-Kit

Then enter FHIR-AI-Hackathon-Kit/Dockerfhir:

	cd FHIR-AI-Hackathon-Kit/Dockerfhir


**For the next step you need to have [docker](https://www.docker.com/products/docker-desktop/) installed and running on your system.**

Run: 

```
docker pull intersystems/irishealth-community:latest-em
```

to download the container, and 

```
docker-compose build
```

to build the deployment. These two steps will take a while to run. But then you can start up the container with: 

```
docker-compose up -d 
```
the -d flag makes it run in the background. 

**1. Access the IRIS Management Portal**
Open your browser and go to:
 **[http://localhost:32783/csp/sys/UtilHome.csp](http://localhost:32783/csp/sys/UtilHome.csp)**  
**Login Credentials:**
- **Username:** `_SYSTEM`
- **Password:** `ISCDEMO`

In the docker compose file, the container ports 1972 and 52773 have been mapped to 32782 and 32783 respectively. 

Note, sometimes it takes a minute for the management portal to come online here, so if nothing appears at the link above, wait a couple of minutes, then refresh the page. 

### Next steps

Now you have installed the FHIR server you can continue with the main tutorial with [1-Using-FHIR-SQL-builder](1-Using-FHIR-SQL-Builder.ipynb), or check out the additional demos on [Accessing FHIR Resources](../Additional-demos/Accessing-FHIR-resources.ipynb), 
[Adding FHIR Data](../Additional-demos\Adding-FHIR-data-to-IRIS-health.ipynb) and [making synthetic FHIR data](../Additional-demos/Making-synthetic-fhir-data.md).
