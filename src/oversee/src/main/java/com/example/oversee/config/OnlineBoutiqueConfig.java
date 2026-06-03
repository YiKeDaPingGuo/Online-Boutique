package com.example.oversee.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
@ConfigurationProperties(prefix = "online.boutique")
@Data
public class OnlineBoutiqueConfig {
    private List<ServiceInfo> services;

    @Data
    public static class ServiceInfo {
        private String name;
        private String url;
    }
}