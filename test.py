

client = Client()
protein_entry = client.get("Q283350", load=True)
ensembl_ids = client.
print(ensembl_ids)