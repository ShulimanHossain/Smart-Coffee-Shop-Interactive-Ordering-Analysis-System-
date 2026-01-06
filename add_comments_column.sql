-- SQL script to add comments column to Order_details table
-- This allows customers to add notes/suggestions for each item (e.g., "No ice", "Extra sugar")
-- Comments are temporary and will be cleared when order is completed

USE Cafe_ML;

-- Add comments column to Order_details table
ALTER TABLE Order_details 
ADD COLUMN comments VARCHAR(255) DEFAULT NULL 
COMMENT 'Temporary customer notes/suggestions for the item (e.g., No ice, Extra sugar)';
