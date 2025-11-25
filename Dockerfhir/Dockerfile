ARG IMAGE=intersystemsdc/irishealth-community:latest
FROM $IMAGE as builder

WORKDIR /home/irisowner/irisdev
#RUN chown ${ISC_PACKAGE_MGRUSER}:${ISC_PACKAGE_IRISGROUP} /opt/irisapp


# copy all the source into container and run iris. also run a initial script
RUN --mount=type=bind,src=.,dst=. \
    iris start IRIS && \
    iris merge IRIS merge.cpf && \
	iris session IRIS < iris.script && \
    iris stop IRIS quietly

USER root
RUN sed -i -e 's|http://localhost:52773/crud/_spec|/fhirUI/irisfhir_swagger.json|g' /usr/irissys/csp/swagger-ui/index.html
RUN sed -i -e 's|http://localhost:52773/crud/_spec|/fhirUI/irisfhir_swagger.json|g' /usr/irissys/csp/swagger-ui/swagger-initializer.js
RUN sed -i -e 's|http://localhost:52773/crud/_spec|/fhirUI/irisfhir_swagger.json|g' /usr/irissys/csp/swagger-ui/swagger-ui-bundle.js

RUN sed -i -e 's|/fhir/r4|/csp/healthshare/demo/fhir/r4|g' /usr/irissys/csp/fhir/fhirUI/resources/js/myFHIR.js


USER ${ISC_PACKAGE_MGRUSER}

FROM $IMAGE as final

ADD --chown=${ISC_PACKAGE_MGRUSER}:${ISC_PACKAGE_IRISGROUP} https://github.com/grongierisc/iris-docker-multi-stage-script/releases/latest/download/copy-data.py /irisdev/app/copy-data.py

RUN --mount=type=bind,source=/,target=/builder/root,from=builder \
    cp -f /builder/root/usr/irissys/iris.cpf /usr/irissys/iris.cpf && \
    python3 /irisdev/app/copy-data.py -c /usr/irissys/iris.cpf -d /builder/root/