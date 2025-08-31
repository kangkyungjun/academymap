from django.contrib import admin
from .models import Data

# Register your models here.
@admin.register(Data)
class DataAdmin(admin.ModelAdmin):
    list_display = ['상호명', '시군구명', '시도명', '별점', '수강료_평균']
    list_filter = ['시도명', '시군구명', '과목_수학', '과목_영어', '대상_초등', '대상_중등', '대상_고등']
    search_fields = ['상호명', '도로명주소', '지번주소']
    list_per_page = 50
    
# Import enhanced admin configurations
try:
    from . import admin_enhanced
except ImportError:
    # Enhanced admin not available yet (during migrations, etc.)
    pass

# Import operator admin configurations
try:
    from . import operator_admin
except ImportError:
    # Operator admin not available yet (during migrations, etc.)
    pass

# Import analytics admin configurations
try:
    from . import analytics_admin
except ImportError:
    # Analytics admin not available yet (during migrations, etc.)
    pass

# Import SEO admin configurations
try:
    from . import seo_admin
except ImportError:
    # SEO admin not available yet (during migrations, etc.)
    pass
