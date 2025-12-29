from django import forms
from .models import StockEntry

class StockEntryForm(forms.ModelForm):
    class Meta:
        model = StockEntry
        fields = ['quantity', 'location', 'damaged_quantity']
        widgets = {
            'quantity': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Qty'}),
            'location': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'WH'}),
            'damaged_quantity': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg border-danger text-danger', 
                'placeholder': 'Damaged'
            })
        }