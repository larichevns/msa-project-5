package com.example.batchprocessing;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import org.springframework.batch.core.BatchStatus;
import org.springframework.batch.core.JobExecution;
import org.springframework.batch.core.JobExecutionListener;
import org.springframework.jdbc.core.DataClassRowMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

@Component
public class JobCompletionNotificationListener implements JobExecutionListener {

	private static final Logger log = LoggerFactory.getLogger(JobCompletionNotificationListener.class);

	private final JdbcTemplate jdbcTemplate;

	public JobCompletionNotificationListener(JdbcTemplate jdbcTemplate) {
		this.jdbcTemplate = jdbcTemplate;
	}

	@Override
	public void afterJob(JobExecution jobExecution) {
		if (jobExecution.getStatus() == BatchStatus.COMPLETED) {
			log.info("!!! JOB FINISHED! Time to verify the results");
			log.info("Job execution details:");
			log.info("  - Job Name: {}", jobExecution.getJobInstance().getJobName());
			log.info("  - Start Time: {}", jobExecution.getStartTime());
			log.info("  - End Time: {}", jobExecution.getEndTime());
			log.info("  - Status: {}", jobExecution.getStatus());
			log.info("  - Exit Status: {}", jobExecution.getExitStatus().getExitCode());

			jdbcTemplate
				.query("SELECT productId, productSku, productName, productAmount, productData FROM products",
					new DataClassRowMapper<>(Product.class))
				.forEach(product -> log.info("Found <{{}}> in the database.", product));

			Long totalProducts = jdbcTemplate.queryForObject(
				"SELECT COUNT(*) FROM products", Long.class);
			log.info("Total products in database: {}", totalProducts);

			log.info("=======================================================");
			log.info("Job completed successfully!");
			log.info("=======================================================");
		} else if (jobExecution.getStatus() == BatchStatus.FAILED) {
			log.error("!!! JOB FAILED! Please check the logs for errors");
			log.error("Job execution details:");
			log.error("  - Job Name: {}", jobExecution.getJobInstance().getJobName());
			log.error("  - Status: {}", jobExecution.getStatus());
			log.error("  - Exit Status: {}", jobExecution.getExitStatus().getExitCode());
			log.error("  - Exit Description: {}", jobExecution.getExitStatus().getExitDescription());

			jobExecution.getAllFailureExceptions().forEach(throwable ->
				log.error("Exception during job execution: ", throwable)
			);
		}
	}
}
