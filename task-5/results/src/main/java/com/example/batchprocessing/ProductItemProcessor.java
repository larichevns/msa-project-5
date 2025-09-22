package com.example.batchprocessing;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;

import org.springframework.batch.item.ItemProcessor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.DataClassRowMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

import java.util.concurrent.atomic.AtomicReference;

@Component
public class ProductItemProcessor implements ItemProcessor<Product, Product> {

	private static final Logger log = LoggerFactory.getLogger(ProductItemProcessor.class);

	@Autowired
	private JdbcTemplate jdbcTemplate;

	private final Counter processedItemsCounter;
	private final Counter loyaltyUpdatesCounter;
	private final Counter errorCounter;
	private final Timer processingTimer;

	@Autowired
	public ProductItemProcessor(MeterRegistry registry) {
		this.processedItemsCounter = Counter.builder("batch.items.processed")
				.description("Number of items processed")
				.tag("processor", "product")
				.register(registry);

		this.loyaltyUpdatesCounter = Counter.builder("batch.loyalty.updates")
				.description("Number of loyalty data updates")
				.register(registry);

		this.errorCounter = Counter.builder("batch.processing.errors")
				.description("Number of processing errors")
				.tag("type", "loyalty_lookup")
				.register(registry);

		this.processingTimer = Timer.builder("batch.item.processing.time")
				.description("Time taken to process each item")
				.tag("processor", "product")
				.register(registry);
	}

    @Override
	public Product process(final Product product) {
		return processingTimer.record(() -> {
			// Add MDC context for better log correlation
			MDC.put("productId", String.valueOf(product.productId()));
			MDC.put("productSku", String.valueOf(product.productSku()));
			MDC.put("jobName", "importProductJob");

			try {
				log.info("Processing product: {}", product);

				final Long productId = product.productId();
				final Long productSku = product.productSku();
				final String productName = product.productName();
				final Long productAmount = product.productAmount();
				String productData = product.productData();

				try {
					String sql = "SELECT * FROM loyalty_data WHERE productSku = ?";
					Loyalty loyaltyData = jdbcTemplate.query(sql, new DataClassRowMapper<>(Loyalty.class), productSku)
							.stream()
							.findFirst()
							.orElse(null);

					if (loyaltyData != null && loyaltyData.loyaltyStatus() != null) {
						productData = loyaltyData.loyaltyStatus();
						log.info("Updated product {} with loyalty data: {}", productSku, productData);
						loyaltyUpdatesCounter.increment();
					} else {
						log.debug("No loyalty data found for SKU {}", productSku);
					}
				} catch (Exception e) {
					log.error("Error processing loyalty data for product {}: {}", productSku, e.getMessage(), e);
					errorCounter.increment();
				}

				Product transformedProduct = new Product(productId, productSku, productName, productAmount, productData);
				log.info("Successfully transformed product: {}", transformedProduct);

				processedItemsCounter.increment();
				return transformedProduct;

			} finally {
				// Clear MDC context
				MDC.clear();
			}
		});
	}

}
