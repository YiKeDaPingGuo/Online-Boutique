package com.example.oversee.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
@ConfigurationProperties(prefix = "online.boutique")
@Data
public class ServiceConfig {
    private List<Service> services;

    @Data
    public static class Service {
        private String name;
        private String protocol;
        private String host;
        private int port;
    }
}