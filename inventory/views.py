from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum

from .models import Brand, Product, StockEntry
from .forms import StockEntryForm
from django.db import models
from django.contrib.auth.models import User 
# 1. Select Brand
@login_required
def brand_select(request):
    brands = Brand.objects.all()
    return render(request, 'inventory/brand_select.html', {'brands': brands})

# 2. Search Items
from django.db.models import Sum, Value, Q
from django.db.models.functions import Coalesce

@login_required
def product_search(request):
    brand_ids = request.GET.getlist('brands')
    query = request.GET.get('q', '')
    
    if not brand_ids:
        return redirect('brand_select')

    selected_brands = Brand.objects.filter(id__in=brand_ids)
    
    # Start with an empty list
    products = Product.objects.none()

    if query:
        # 1. Filter by Brand AND Search Query
        products = Product.objects.filter(
            brand__id__in=brand_ids
        ).filter(
            Q(item_code__icontains=query) | 
            Q(description__icontains=query) | 
            Q(upc_code__icontains=query)
        )
        
        # 2. THE FIX: Attach 'user_total' to every product row
        # This sums up quantity ONLY for the logged-in user
        products = products.annotate(
            user_total=Coalesce(
                Sum('entries__quantity', filter=Q(entries__user=request.user)), 
                Value(0)
            ),
            # NEW: Calculate damaged sum
            user_damaged=Coalesce(
                Sum('entries__damaged_quantity', filter=Q(entries__user=request.user)), 
                Value(0)
            )
        ).order_by('-user_total', 'item_code')

        # 3. Limit to 100 for performance
        products = products[:100]

    return render(request, 'inventory/search.html', {
        'products': products, 
        'selected_brands': selected_brands,
        'brand_ids': brand_ids,
        'query': query
    })

# 3. Item Detail & Counting
@login_required
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    user_entries = StockEntry.objects.filter(product=product, user=request.user).order_by('-timestamp')
    total = user_entries.aggregate(Sum('quantity'))['quantity__sum'] or 0
    
    # Get last location
    initial_loc = request.session.get('last_location', '')

    if request.method == 'POST':
        form = StockEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.product = product
            entry.user = request.user
            entry.save()
            request.session['last_location'] = entry.location
            
            # --- CHECK WHERE TO REDIRECT ---
            # If the form has a hidden field 'next', go there.
            next_url = request.POST.get('next')
            if next_url:
                return redirect(next_url)
            
            return redirect('product_detail', product_id=product.id)
    else:
        form = StockEntryForm(initial={'location': initial_loc})

    return render(request, 'inventory/detail.html', {
        'product': product, 'form': form, 'entries': user_entries, 'total': total
    })

@login_required
def product_popup(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    user_entries = StockEntry.objects.filter(product=product, user=request.user).order_by('-timestamp')
    
    # Calculate both totals
    total_good = user_entries.aggregate(Sum('quantity'))['quantity__sum'] or 0
    total_damaged = user_entries.aggregate(Sum('damaged_quantity'))['damaged_quantity__sum'] or 0
    
    initial_loc = request.session.get('last_location', '')
    form = StockEntryForm(initial={'location': initial_loc})
    
    return render(request, 'inventory/popup_content.html', {
        'product': product, 
        'form': form, 
        'entries': user_entries, 
        'total': total_good,
        'total_damaged': total_damaged # Pass this to template
    })

from django.core.paginator import Paginator
@user_passes_test(lambda u: u.is_staff)
def master_report(request):
    teams = User.objects.exclude(is_superuser=True).order_by('username')
    brands = Brand.objects.all().order_by('name')

    # --- FILTERING LOGIC ---
    products = Product.objects.all().order_by('item_code')
    
    # 1. Filter by Brand (Multi-select)
    selected_brand_ids = request.GET.getlist('brands')
    if selected_brand_ids:
        products = products.filter(brand__id__in=selected_brand_ids)
        # Convert strings to ints for the template to check checkboxes
        selected_brand_ids = [int(id) for id in selected_brand_ids]

    # 2. Filter by Search Text
    query = request.GET.get('q', '')
    if query:
        products = products.filter(
            models.Q(item_code__icontains=query) | 
            models.Q(description__icontains=query) |
            models.Q(upc_code__icontains=query)
        )

    # --- PAGINATION (Critical for 29k items) ---
    paginator = Paginator(products, 50) # Show 50 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # --- MATRIX BUILDER (Only for the 50 items on this page) ---
    # We prefetch entries to prevent 50 * 8 database queries
    page_products = page_obj.object_list
    
    # Prefetch logic: get entries only for these products
    # This is a bit advanced, but keeps it fast.
    products_with_data = []
    
    for p in page_products:
        row = {
            'id': p.id,
            'code': p.item_code, 
            'desc': p.description, 
            'brand': p.brand.name,
            'system_stock': p.system_stock,
            'cols': []
        }
        
        # 1. Get all entries for this product
        entries = p.entries.all() 
        
        # 2. Calculate Totals
        # Sum of Good Quantity (Existing)
        grand_total = sum(e.quantity for e in entries)
        
        # NEW: Sum of Damaged Quantity
        grand_damaged = sum(e.damaged_quantity for e in entries)

        for team in teams:
            team_entries = [e for e in entries if e.user_id == team.id]
            team_total = sum(e.quantity for e in team_entries)
            
            # Note: We are NOT showing damaged per team in the columns, just the total at the end
            row['cols'].append({
                'user_id': team.id,
                'total': team_total,
                'tooltip': " + ".join([f"{e.quantity}" for e in team_entries])
            })
            
        row['grand_total'] = grand_total
        row['total_damaged'] = grand_damaged  # <--- Pass this to the template
        row['variance'] = grand_total - p.system_stock # Variance ignores damaged
        
        products_with_data.append(row)

    return render(request, 'inventory/report.html', {
        'teams': teams,
        'brands': brands,
        'page_obj': page_obj, # The paginator object
        'data': products_with_data,
        'selected_brands': selected_brand_ids,
        'query': query,
    })

def report_detail(request, product_id, user_id):
    product = get_object_or_404(Product, id=product_id)
    target_user = get_object_or_404(User, id=user_id)
    
    entries = StockEntry.objects.filter(
        product=product, 
        user=target_user
    ).order_by('-timestamp')
    
    # Calculate BOTH totals
    # We use a dictionary unpacking trick to get both sums in one query
    aggregates = entries.aggregate(
        sum_good=Sum('quantity'),
        sum_damaged=Sum('damaged_quantity')
    )
    
    total = aggregates['sum_good'] or 0
    total_damaged = aggregates['sum_damaged'] or 0
    
    return render(request, 'inventory/report_detail.html', {
        'product': product,
        'target_user': target_user,
        'entries': entries,
        'total': total,
        'total_damaged': total_damaged, # Pass this new variable
    })



# inventory/views.py

@login_required
def delete_entry(request, entry_id):
    # 1. Find the entry, BUT only if it belongs to the logged-in user
    entry = get_object_or_404(StockEntry, id=entry_id, user=request.user)
    
    # 2. Delete it
    entry.delete()
    
    # 3. Go back to wherever the user came from (Search page or Detail page)
    return redirect(request.META.get('HTTP_REFERER', 'brand_select'))


@login_required
def home_redirect(request):
    # 1. Check if the user is Admin / Staff
    if request.user.is_staff:
        return redirect('master_report')
    
    # 2. Everyone else (Teams) goes to Brand Selection
    return redirect('brand_select')