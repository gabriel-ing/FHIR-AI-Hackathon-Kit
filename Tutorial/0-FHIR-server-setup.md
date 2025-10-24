# Setting up IRIS-Health with a FHIR server

In this tutorial, we will be using an instance of IRIS-health with a FHIR server, from within a docker container. There are lots of good tutorials on how to use [IRIS-community editions with docker](https://community.intersystems.com/post/running-intersystems-iris-docker-step-step-guide-part-1-basics-custom-dockerfile), but for now I am going to use a pre-loaded build. I've cloned a [IRIS-health + FHIR docker starter repo](https://github.com/pjamiesointersystems/Dockerfhir/tree/main) into this repository so I could change some things, notably I am pre-loading a different dataset, I am also publishing other ports.

To start, clone this repository: 

	git clone https://github.com/gabriel-ing/FHIR-AI-Hackathons

Then enter FHIR-AI-Hackathons/Dockerfhir:

	cd FHIR-AI-Hackathons/Dockerfhir

and run: 

	docker pull containers.intersystems.com/intersystems/irishealth-community:latest-em

to download the container, and 

	docker-compose build 

to build the deployment. These two steps will take a while to run. But then you can start up the container with: 

	docker-compose up -d 

the -d flag makes it run in the background. 

**1. Access the IRIS Management Portal**
Open your browser and go to:
 **[http://localhost:32783/csp/sys/UtilHome.csp](http://localhost:32783/csp/sys/UtilHome.csp)**  
**Login Credentials:**
- **Username:** `_SYSTEM`
- **Password:** `ISCDEMO`

In the docker compose file, I have mapped the container ports 1972 and 52773 to 32782 and 32783. 

### Next steps

Now you have installed the FHIR server you can continue with the main tutorial with [1-Using-FHIR-SQL-builder](".\1-Using-FHIR-SQL-Builder.ipynb")