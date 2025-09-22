package com.example.batchprocessing.controller;

import io.micrometer.tracing.Tracer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.batch.core.Job;
import org.springframework.batch.core.JobParameters;
import org.springframework.batch.core.JobParametersBuilder;
import org.springframework.batch.core.launch.JobLauncher;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import jakarta.servlet.http.HttpServletRequest;
import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/jobs")
public class JobController {

    private static final Logger logger = LoggerFactory.getLogger(JobController.class);

    @Autowired
    private JobLauncher jobLauncher;

    @Autowired
    private Job importProductJob;

    @Autowired
    private Tracer tracer;

    @PostMapping("/trigger")
    public ResponseEntity<Map<String, Object>> triggerJob(HttpServletRequest request) {
        Map<String, Object> response = new HashMap<>();

        try {
            // Get trace information
            String traceId = tracer.currentSpan() != null ?
                tracer.currentSpan().context().traceId() : "no-trace";
            String spanId = tracer.currentSpan() != null ?
                tracer.currentSpan().context().spanId() : "no-span";
            String uri = request.getRequestURI();
            String method = request.getMethod();

            // Add trace info to MDC for logging
            MDC.put("traceId", traceId);
            MDC.put("spanId", spanId);
            MDC.put("uri", uri);
            MDC.put("method", method);

            logger.info("API request received to trigger Spring Batch job. TraceId: {}, SpanId: {}, URI: {}, Method: {}",
                traceId, spanId, uri, method);

            // Create job parameters with timestamp to ensure unique execution
            JobParameters jobParameters = new JobParametersBuilder()
                .addLong("startTime", System.currentTimeMillis())
                .addString("traceId", traceId)
                .addString("spanId", spanId)
                .toJobParameters();

            // Launch the job
            logger.info("Starting Spring Batch job execution with traceId: {}", traceId);
            var jobExecution = jobLauncher.run(importProductJob, jobParameters);

            // Prepare response
            response.put("status", "success");
            response.put("message", "Job triggered successfully");
            response.put("jobExecutionId", jobExecution.getId());
            response.put("traceId", traceId);
            response.put("spanId", spanId);
            response.put("uri", uri);
            response.put("method", method);
            response.put("timestamp", System.currentTimeMillis());

            logger.info("Spring Batch job completed successfully. JobExecutionId: {}, TraceId: {}",
                jobExecution.getId(), traceId);

            return ResponseEntity.ok(response);

        } catch (Exception e) {
            String traceId = tracer.currentSpan() != null ?
                tracer.currentSpan().context().traceId() : "no-trace";

            logger.error("Error executing Spring Batch job. TraceId: {}, Error: {}", traceId, e.getMessage(), e);

            response.put("status", "error");
            response.put("message", "Failed to trigger job: " + e.getMessage());
            response.put("traceId", traceId);
            response.put("timestamp", System.currentTimeMillis());

            return ResponseEntity.internalServerError().body(response);
        } finally {
            // Clean up MDC
            MDC.clear();
        }
    }

    @GetMapping("/status")
    public ResponseEntity<Map<String, Object>> getStatus(HttpServletRequest request) {
        Map<String, Object> response = new HashMap<>();

        String traceId = tracer.currentSpan() != null ?
            tracer.currentSpan().context().traceId() : "no-trace";
        String spanId = tracer.currentSpan() != null ?
            tracer.currentSpan().context().spanId() : "no-span";
        String uri = request.getRequestURI();
        String method = request.getMethod();

        MDC.put("traceId", traceId);
        MDC.put("spanId", spanId);
        MDC.put("uri", uri);
        MDC.put("method", method);

        logger.info("Status check request received. TraceId: {}, SpanId: {}, URI: {}",
            traceId, spanId, uri);

        response.put("status", "healthy");
        response.put("service", "Spring Batch ETL Service");
        response.put("traceId", traceId);
        response.put("spanId", spanId);
        response.put("timestamp", System.currentTimeMillis());

        MDC.clear();
        return ResponseEntity.ok(response);
    }
}