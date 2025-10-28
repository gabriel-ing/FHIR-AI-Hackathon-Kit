# Use the official InterSystems IRIS for Health Community Edition image
FROM intersystems/irishealth-community:latest-em

# Switch to the root user to perform administrative tasks
USER root

# Install prerequisites and Java (Temurin JDK 17 for both amd64 and arm64)
RUN apt-get update && \
    apt-get install -y wget gnupg curl lsb-release && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://packages.adoptium.net/artifactory/api/gpg/key/public | gpg --dearmor -o /etc/apt/keyrings/adoptium.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/adoptium.gpg] https://packages.adoptium.net/artifactory/deb $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/adoptium.list && \
    apt-get update && \
    apt-get install -y temurin-17-jdk && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


# Create necessary directories for scripts, configuration, and data storage
RUN mkdir -p /scripts            # Directory for storing setup scripts
RUN mkdir -p /data/ifconfig       # Directory for configuration data
RUN mkdir -p /fhirdata            # Directory for storing FHIR-related data

# Set JAVA_HOME dynamically based on architecture
# writes the correct SetServerInfo call into a temporary ObjectScript file
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then \
        JAVA_HOME="/usr/lib/jvm/temurin-11-jdk-amd64"; \
    elif [ "$ARCH" = "arm64" ]; then \
        JAVA_HOME="/usr/lib/jvm/temurin-11-jdk-arm64"; \
    else \
        echo "Unsupported architecture: $ARCH" && exit 1; \
    fi 
    # echo "Set sc = ##class(%SYS.ExternalLanguage.Server).SetServerInfo(\"FHIR_Validation_Server\", \"java\", \"${JAVA_HOME}\", \"\", \"\")" > /scripts/setjava.script && \
    # echo 'If $$$ISERR(sc) { Write "Error setting Java Home", ! Quit }' >> /scripts/setjava.script && \
    # echo 'Halt' >> /scripts/setjava.script


# Copy FHIR data set into the container
COPY ./fhirdata/100Set /fhirdata/

# Copy configuration merge file for InterSystems IRIS
COPY ./merge/CMF.cpf /merge/CMF.cpf

# Set correct ownership of directories for the IRIS user and group
RUN chown -R ${ISC_PACKAGE_MGRUSER}:${ISC_PACKAGE_IRISGROUP} /data/
RUN chown -R ${ISC_PACKAGE_MGRUSER}:${ISC_PACKAGE_IRISGROUP} /fhirdata/
RUN chown -R ${ISC_PACKAGE_MGRUSER}:${ISC_PACKAGE_IRISGROUP} /merge/

# Copy necessary scripts for configuring the FHIR server and ZPM package manager
COPY ./scripts/fhirserver.script /scripts/fhirserver.script
COPY ./scripts/enablecors.script /scripts/enablecors.script
COPY ./scripts/zpm.script /scripts/zpm.script
COPY ./scripts/fhirvalidator.script /scripts/fhirvalidator.script

# Ensure scripts have the correct ownership
RUN chown -R ${ISC_PACKAGE_MGRUSER}:${ISC_PACKAGE_IRISGROUP} /scripts/

# Switch to the IRIS user for security best practices
USER ${ISC_PACKAGE_MGRUSER}

# Start IRIS, execute the FHIR server setup script, and then stop IRIS
RUN \
iris start IRIS && \
iris session IRIS < /scripts/fhirserver.script && \
iris session IRIS < /scripts/enablecors.script && \
iris stop IRIS quietly 
# iris start IRIS && \
# iris session IRIS < /scripts/fhirvalidator.script && \
# iris stop IRIS quietly

# Ensure the user remains the IRIS user
USER ${ISC_PACKAGE_MGRUSER}

# Expose the necessary ports:
# - 52773: Web interface (Management Portal, FHIR API)
# - 1972: InterSystems IRIS SuperServer (database connectivity)
# - 53773: Optional, used for system monitoring or analytics
EXPOSE 52773 1972 52773 53773

# Set environment variables for IRIS configuration
ENV ISC_DATA_DIRECTORY=/data/ifconfig  
ENV ISC_CPF_MERGE_FILE=/merge/CMF.cpf 

# Define the entrypoint to execute when the container starts
ENTRYPOINT [ "/iris-main" ]
