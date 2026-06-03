package com.example.oversee;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling // 开启定时任务
public class OverseeApplication {
    public static void main(String[] args) {
        SpringApplication.run(OverseeApplication.class, args);
    }
}