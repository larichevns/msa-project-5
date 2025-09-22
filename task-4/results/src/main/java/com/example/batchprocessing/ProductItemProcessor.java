package com.example.batchprocessing;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

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

    @Override
	public Product process(final Product product) {
		log.info("Processing product: {}", product);

		final Long productId = product.productId();
		final Long productSku = product.productSku();
		final String productName = product.productName();
		final Long productAmount = product.productAmount();
		String productData = product.productData();

		try {
			String sql = "SELECT * FROM loyality_data WHERE productSku = ?";
			jdbcTemplate.query(sql, new DataClassRowMapper<>(Loyality.class), productSku)
					.stream()
					.findFirst()
					.ifPresent(loyality -> {
						log.info("Found loyalty data for SKU {}: {}", productSku, loyality.loyalityData());
					});

			Loyality loyalityData = jdbcTemplate.query(sql, new DataClassRowMapper<>(Loyality.class), productSku)
					.stream()
					.findFirst()
					.orElse(null);

			if (loyalityData != null && loyalityData.loyalityData() != null) {
				productData = loyalityData.loyalityData();
				log.info("Updated product {} with loyalty data: {}", productSku, productData);
			}
		} catch (Exception e) {
			log.error("Error processing loyalty data for product {}: {}", productSku, e.getMessage());
		}

		Product transformedProduct = new Product(productId, productSku, productName, productAmount, productData);
		log.info("Transformed product: {}", transformedProduct);

		return transformedProduct;
	}

}
