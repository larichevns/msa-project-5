package com.example.batchprocessing.config;

import io.micrometer.tracing.Tracer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.filter.OncePerRequestFilter;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;

@Configuration
public class TracingConfig {

    @Bean
    public TracingFilter tracingFilter(Tracer tracer) {
        return new TracingFilter(tracer);
    }

    public static class TracingFilter extends OncePerRequestFilter {

        private final Tracer tracer;

        public TracingFilter(Tracer tracer) {
            this.tracer = tracer;
        }

        @Override
        protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                      FilterChain filterChain) throws ServletException, IOException {

            // Add trace ID to response headers for client correlation
            if (tracer.currentSpan() != null) {
                String traceId = tracer.currentSpan().context().traceId();
                String spanId = tracer.currentSpan().context().spanId();

                response.setHeader("X-Trace-Id", traceId);
                response.setHeader("X-Span-Id", spanId);
            }

            filterChain.doFilter(request, response);
        }
    }
}