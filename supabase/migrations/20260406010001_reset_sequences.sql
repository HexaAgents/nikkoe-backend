-- Reset all auto-increment sequences to match the current max id in each table.
-- Required after bulk data import that didn't update sequences.
-- Sequence names use the original PascalCase naming convention.

SELECT setval('"Category_id_seq"', COALESCE((SELECT MAX(id) FROM "category"), 1));
SELECT setval('"Supplier_id_seq"', COALESCE((SELECT MAX(id) FROM "supplier"), 1));
SELECT setval('"Location_id_seq"', COALESCE((SELECT MAX(id) FROM "location"), 1));
SELECT setval('"Item_id_seq"', COALESCE((SELECT MAX(id) FROM "item"), 1));
SELECT setval('"Customer_id_seq"', COALESCE((SELECT MAX(id) FROM "customer"), 1));
SELECT setval('"Channel_id_seq"', COALESCE((SELECT MAX(id) FROM "channel"), 1));
SELECT setval('"Currency_id_seq"', COALESCE((SELECT MAX(id) FROM "currency"), 1));
SELECT setval('"Sale_id_seq"', COALESCE((SELECT MAX(id) FROM "sale"), 1));
SELECT setval('"Receipt_id_seq"', COALESCE((SELECT MAX(id) FROM "receipt"), 1));
SELECT setval('"Stock_id_seq"', COALESCE((SELECT MAX(id) FROM "stock"), 1));
SELECT setval('"Sale_Stock_id_seq"', COALESCE((SELECT MAX(id) FROM "sale_stock"), 1));
SELECT setval('"Receipt_Stock_id_seq"', COALESCE((SELECT MAX(id) FROM "receipt_stock"), 1));
SELECT setval('"Item_supplier_id_seq"', COALESCE((SELECT MAX(id) FROM "item_supplier"), 1));
SELECT setval('"Transfer_id_seq"', COALESCE((SELECT MAX(id) FROM "transfer"), 1));
SELECT setval('"User_id_seq"', COALESCE((SELECT MAX(id) FROM "user"), 1));
