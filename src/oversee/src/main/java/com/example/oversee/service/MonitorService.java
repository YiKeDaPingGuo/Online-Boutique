package com.example.oversee.service;

import com.example.oversee.config.ServiceConfig;
import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import io.grpc.health.v1.HealthCheckRequest;
import io.grpc.health.v1.HealthCheckResponse;
import io.grpc.health.v1.HealthGrpc;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import lombok.RequiredArgsConstructor;
import org.springframework.data.redis.connection.RedisStandaloneConfiguration;
import org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import javax.annotation.PostConstruct;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

@Service
@RequiredArgsConstructor
public class MonitorService {
    private final ServiceConfig serviceConfig;
    private final MeterRegistry meterRegistry;
    private final RestTemplate restTemplate = new RestTemplate();
    private final ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(15);

    @PostConstruct
    public void startMonitor() {
        for (ServiceConfig.Service service : serviceConfig.getServices()) {
            scheduler.scheduleAtFixedRate(
                    new Runnable() {
                        @Override
                        public void run() {
                            checkService(service);
                        }
                    },
                    0, 5, TimeUnit.SECONDS
            );
        }
    }

    private void checkService(ServiceConfig.Service service) {
        String name = service.getName();
        long start = System.currentTimeMillis();
        boolean success = false;

        try {
            // Java 8：只能用传统 switch（冒号+break）
            String protocol = service.getProtocol();
            if ("http".equals(protocol)) {
                checkHttp(service);
            } else if ("grpc".equals(protocol)) {
                checkGrpc(service);
            } else if ("redis".equals(protocol)) {
                checkRedis(service);
            }
            success = true;
        } catch (Exception e) {
            incrementError(name);
        } finally {
            double latency = System.currentTimeMillis() - start;
            setLatency(name, latency);
            if (success) {
                incrementRequest(name);
            }
        }
    }

    private void checkHttp(ServiceConfig.Service service) {
        String url = "http://" + service.getHost() + ":" + service.getPort();
        restTemplate.getForObject(url, String.class);
    }

    private void checkGrpc(ServiceConfig.Service service) {
        ManagedChannel channel = ManagedChannelBuilder.forAddress(service.getHost(), service.getPort())
                .usePlaintext().build();
        HealthGrpc.HealthBlockingStub stub = HealthGrpc.newBlockingStub(channel);
        HealthCheckResponse response = stub.check(HealthCheckRequest.getDefaultInstance());
        channel.shutdown();

        if (response.getStatus() != HealthCheckResponse.ServingStatus.SERVING) {
            throw new RuntimeException("gRPC not serving");
        }
    }

    private void checkRedis(ServiceConfig.Service service) {
        RedisStandaloneConfiguration cfg = new RedisStandaloneConfiguration(
                service.getHost(), service.getPort()
        );
        LettuceConnectionFactory factory = new LettuceConnectionFactory(cfg);
        factory.afterPropertiesSet();
        factory.getConnection().ping();
        factory.destroy();
    }

    private void incrementRequest(String service) {
        Counter.builder("online_boutique_requests_total")
                .tag("service", service)
                .register(meterRegistry)
                .increment();
    }

    private void incrementError(String service) {
        Counter.builder("online_boutique_errors_total")
                .tag("service", service)
                .register(meterRegistry)
                .increment();
    }

    private void setLatency(String service, double latency) {
        Gauge.builder("online_boutique_request_latency", () -> latency)
                .tag("service", service)
                .register(meterRegistry);
    }
}