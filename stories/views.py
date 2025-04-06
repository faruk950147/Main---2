from django.shortcuts import render,redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.views import generic
from django.utils import timezone
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse, HttpResponseBadRequest
from django.db.models import Min, Max
import json
from stories.models import (
    Category,Brand,Product, Images,Color,Size,Variants,Slider,Banner,ProductFuture,Review
)
# from cart.forms import CartForm

# Create your views here.
@method_decorator(never_cache, name='dispatch')
class HomeView(generic.View):
    def get(self, request):
        context = {
            'sliders': Slider.objects.filter(status=True).select_related('product').prefetch_related('product__product_variants').order_by('id'),
            'banners': Banner.objects.filter(status=True).select_related('product').prefetch_related('product__product_variants').order_by('id')[:3],
            'side_deals_banners': Banner.objects.filter(status=True, side_deals=True, side_deals_is_active=True).select_related('product').prefetch_related('product__product_variants').order_by('id')[:1],
            'deals_products': Product.objects.filter(offers_deadline__isnull=False,  is_timeline=True, deals=True, status=True).select_related('category', 'brand').prefetch_related('product_variants').order_by("id")[:6],
            'current_time': timezone.now(),
            'new_collections': Product.objects.filter(status=True, new_collection=True).select_related('category', 'brand').prefetch_related('product_variants__color', 'product_variants__size').order_by('id')[:4],
            'girls_collections': Product.objects.filter(status=True, girls_collection=True).select_related('category', 'brand').prefetch_related('product_variants__color', 'product_variants__size').order_by('id')[:4],
            'men_collections': Product.objects.filter(status=True, men_collection=True).select_related('category', 'brand').prefetch_related('product_variants__color', 'product_variants__size').order_by('id')[:4],
            'latest_collections': Product.objects.filter(status=True, latest_collection=True).select_related('category', 'brand').prefetch_related('product_variants__color', 'product_variants__size').order_by('id')[:4],
            'pick_collections': Product.objects.filter(status=True, pick_collection=True).select_related('category', 'brand').prefetch_related('product_variants__color', 'product_variants__size').order_by('id')[:4],   
        }
        return render(request, 'stories/home.html', context)

@method_decorator(never_cache, name='dispatch')
class SingleProductView(generic.View):
    def get(self, request, id):
        product = get_object_or_404(Product.objects.prefetch_related('product_variants'), id=id)

        related_products = Product.objects.filter(category=product.category).exclude(id=product.id).select_related('category').prefetch_related('product_variants__color', 'product_variants__size').order_by('-id')[:4]

        reviews = Review.objects.filter(product=product, status=True).select_related('user').prefetch_related('product')
        reviews_total = reviews.count()

        variants = Variants.objects.filter(product=product).select_related('size', 'color')

        size_variants = variants.filter(size__isnull=False).order_by('size')
        color_variants = variants.filter(color__isnull=False).order_by('color')

        # Creating unique size and color dictionaries
        unique_sizes = {variant.size.id: {'size': variant.size, 'image': variant.image or 'No Image Available', 'price': variant.price} for variant in size_variants}
        unique_colors = {variant.color.id: {'color': variant.color, 'image': variant.image or 'No Image Available', 'price': variant.price} for variant in color_variants}

        # Selecting the size_variants[0] size and color variant for default selection
        if size_variants.exists():
            selected_size_variant = size_variants[0]
            selected_size_id = selected_size_variant.size_id
            selected_size_title = selected_size_variant.size.title
            selected_size_image = selected_size_variant.image or 'No Image Available'
            selected_price = selected_size_variant.price
        else:
            selected_size_id = None
            selected_size_title = "No Size Selected"
            selected_size_image = 'No Image Available'
            selected_price = None

        if color_variants.exists():
            selected_color_variant = color_variants[0]
            selected_color_id = selected_color_variant.color_id
            selected_color_title = selected_color_variant.color.title
            selected_color_image = selected_color_variant.image or 'No Image Available'
        else:
            selected_color_id = None
            selected_color_title = "No Color Selected"
            selected_color_image = 'No Image Available'

        context = {
            'product': product,
            'related_products': related_products,
            'reviews': reviews,
            'reviews_total': reviews_total,
            'average_review': product.average_review,
            'count_review': product.count_review,
            'unique_sizes': unique_sizes,
            'unique_colors': unique_colors,
            'selected_size_title': selected_size_title,
            'selected_color_title': selected_color_title,
            'selected_price': selected_price,
            'selected_size_id': selected_size_id,
            'selected_color_id': selected_color_id,
            'selected_size_image': selected_size_image,
            'selected_color_image': selected_color_image,
        }
        return render(request, 'stories/single.html', context)

@method_decorator(never_cache, name='dispatch')
class GetColorsBySize(generic.View):
    def get(self, request):
        size_id = request.GET.get('size_id')
        color_id = request.GET.get('color_id')
        product_id = request.GET.get('product_id')

        if not product_id:
            return JsonResponse({'status': 400, 'messages': 'Product ID is required'})

        try:
            size_id = int(size_id) if size_id else None
            product_id = int(product_id)
            color_id = int(color_id) if color_id else None
        except (ValueError, TypeError):
            return JsonResponse({'status': 400, 'messages': 'Invalid size ID, color ID or product ID'})

        # Filter conditions based on product_id and optionally size_id  
        filter_conditions = {'product_id': product_id}
        if size_id:
            filter_conditions['size_id'] = size_id

        variants = list(Variants.objects.filter(**filter_conditions).select_related('size', 'color'))

        if not variants:
            return JsonResponse({'status': 404, 'messages': 'No variants available'})

        # Extract available colors
        colors = [
            {
                'id': variant.color.id,
                'title': variant.color.title,
                'code': variant.color.code,
                'image': variant.image if variant.image else '',
                'price': str(variant.price)
            }
            for variant in variants if variant.color
        ]

        # **Size Available but No Color**
        if size_id and not colors:
            selected_size_title = variants[0].size.title if variants and variants[0].size else None
            selected_price = str(variants[0].price) if variants else "0.00"

            return JsonResponse({
                'status': 200,
                'colors': [],
                'selected_size_title': selected_size_title or "",
                'selected_color_title': "",
                'selected_price': selected_price,
                'messages': f'Only size available: {selected_size_title or " "}'
            })

        # **Color Available but No Size**
        if not size_id and colors:
            selected_color = next((color for color in colors if color['id'] == color_id), None) if color_id else (colors[0] if colors else None)
            selected_color_title = selected_color['title'] if selected_color else ""
            selected_price = selected_color['price'] if selected_color else "0.00"

            return JsonResponse({
                'status': 200,
                'colors': colors,
                'selected_size_title': "",
                'selected_color_title': selected_color_title,
                'selected_price': selected_price,
                'messages': 'Only colors available'
            })

        # **Both Size and Color Available**
        if colors:
            selected_size_title = variants[0].size.title if size_id and variants else ""
            selected_color = next((color for color in colors if color['id'] == color_id), None) if color_id else (colors[0] if colors else None)
            selected_color_title = selected_color['title'] if selected_color else ""
            selected_price = selected_color['price'] if selected_color else "0.00"

            return JsonResponse({
                'status': 200,
                'colors': colors,
                'selected_size_title': selected_size_title,
                'selected_color_title': selected_color_title,
                'selected_price': selected_price,
                'messages': f'Colors available for size {selected_size_title}'
            })

        return JsonResponse({'status': 404, 'messages': 'No variants available'})

@method_decorator(never_cache, name='dispatch')
class ReviewsView(LoginRequiredMixin, generic.View):
    login_url = reverse_lazy('sign')
    def post(self, request):  
        if request.method == "POST":
            try:
                data = json.loads(request.body)
                # Check if updating an existing review
                review_id = data.get("review_id")  
                # Get product ID from request
                product_id = data.get("product_id")  
                # Get the form data
                subject = data.get("subject")
                comment = data.get("comment")
                rate = int(data.get("rate"))
                    
                product = get_object_or_404(Product, id=product_id)  # Ensure product exists
                    
                # Rating validation (1 to 5)
                if not (1 <= rate <= 5):
                    return JsonResponse({"status": 400, "messages": "Invalid rating. Must be between 1 and 5."})

                # Check if the user has already reviewed this product
                if not review_id:
                    existing_review = Review.objects.filter(product=product, user=request.user).first()
                    if existing_review:
                            return JsonResponse({"status": 400, "messages": "You have already reviewed this product."})
                
                if review_id:  # Editing an existing review
                    review = get_object_or_404(Review, id=review_id, user_id=request.user.id)
                    review.subject = subject
                    review.comment = comment
                    review.rate = rate
                    review.save()
                else:  # Creating a new review
                    review = Review()
                    review.product = product
                    review.user_id = request.user.id
                    review.subject = subject
                    review.comment = comment
                    review.rate = rate
                    review.save()
                return JsonResponse({
                    "status": 200,
                    "review_id": review.id,
                    "product_id": review.product.id,
                    "user": review.user.username,
                    "subject": review.subject,
                    "comment": review.comment,
                    "rate": review.rate,  
                    "updated_date": review.updated_date.strftime('%Y-%m-%d %H:%M:%S'),
                    "messages": "Review added successfully"
                })
            except Review.DoesNotExist:
                return JsonResponse({"status": 400, "messages": "Review not found for this user"})
            except Exception as e:
                return JsonResponse({"status": 400, "messages": str(e)})