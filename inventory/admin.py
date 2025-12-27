from django.contrib import admin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin
from .models import Brand, Product, StockEntry

class ProductResource(resources.ModelResource):
    # 1. Map your Excel Columns EXACTLY to Database Fields
    item_code = fields.Field(attribute='item_code', column_name='Item No.')
    upc_code = fields.Field(attribute='upc_code', column_name='Upc Code')
    description = fields.Field(attribute='description', column_name='Item Description')

    system_stock = fields.Field(attribute='system_stock', column_name='System Stock')
    
    # 2. Handle the Brand (Manufacturer Name)
    brand = fields.Field(
        attribute='brand',
        column_name='Manufacturer Name',
        widget=ForeignKeyWidget(Brand, 'name')
    )

    class Meta:
        model = Product
        import_id_fields = ('item_code',) # Use Item No. as the unique key
        # List fields to import
        fields = ('item_code', 'upc_code', 'description', 'brand', 'system_stock',)
        # Check if rows exist to avoid duplicates
        skip_unchanged = True
        report_skipped = True

    # 3. THE MAGIC FIX: Create Brand automatically if it doesn't exist
    def before_import_row(self, row, **kwargs):
        brand_name = row.get('Manufacturer Name')
        if brand_name:
            # This creates the Brand in the DB if it's missing
            Brand.objects.get_or_create(name=str(brand_name).strip())

@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource
    list_display = ('item_code', 'description', 'brand', 'upc_code')
    search_fields = ('item_code', 'description', 'brand__name')
    list_filter = ('brand',)

# Register the other models normally
admin.site.register(Brand)
admin.site.register(StockEntry)