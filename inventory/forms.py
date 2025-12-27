from django import forms
from .models import StockEntry

class StockEntryForm(forms.ModelForm):
    class Meta:
        model = StockEntry
        fields = ['quantity', 'location']
        widgets = {
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter Qty (e.g. 10)'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Warehouse'}),
        }