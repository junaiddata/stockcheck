from django.db import models
from django.contrib.auth.models import User

class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name

class Product(models.Model):
    # We link product to a Brand
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    
    # db_index=True makes searching 29,000 items fast
    item_code = models.CharField(max_length=50, unique=True, db_index=True) 
    upc_code = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    description = models.CharField(max_length=255)
    
    system_stock = models.IntegerField(default=0) 
    def __str__(self):
        return f"{self.item_code} - {self.description}"

class StockEntry(models.Model):
    # This records every time someone hits "Add"
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='entries')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quantity = models.IntegerField() 
    location = models.CharField(max_length=50) # Warehouse/Shelf
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.quantity} items for {self.product.item_code}"