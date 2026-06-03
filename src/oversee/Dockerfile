FROM eclipse-temurin:8-jre
WORKDIR /app
COPY src/oversee/target/*.jar app.jar
ENTRYPOINT ["java", "-jar", "app.jar"]