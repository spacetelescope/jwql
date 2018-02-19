from django.contrib import admin

from .models import ImageData

class ImageDataAdmin(admin.ModelAdmin):
    # fieldsets = [('Filepath', {'fields': ['filepath']}),
    # 			 ('Instrument', {'fields': ['inst']}),
    #              ('Date information', {'fields': ['pub_date']})]
    list_display = ('filename', 'inst', 'pub_date')
    list_filter = ['pub_date']

admin.site.register(ImageData, ImageDataAdmin)
