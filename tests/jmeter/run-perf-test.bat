@echo off
set "JDK_JAVA_OPTIONS=--add-opens java.desktop/javax.swing=ALL-UNNAMED --add-opens java.desktop/java.awt=ALL-UNNAMED --add-opens java.base/java.lang=ALL-UNNAMED --add-opens java.base/java.lang.reflect=ALL-UNNAMED --add-opens java.base/java.util=ALL-UNNAMED --add-opens java.desktop/sun.awt=ALL-UNNAMED"
cd /d "D:\Software Testing and Maintenance\lab\lab3\apache-jmeter-5.6.3\bin"
start jmeter.bat
