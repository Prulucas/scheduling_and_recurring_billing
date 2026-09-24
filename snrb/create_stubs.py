import os

apps = ['barbershop', 'scheduling', 'billing', 'notifications', 'core']
base_dir = r'C:\Users\Pedro Lucas\Documents\Estudos\Python\DRF\scheduling_and_recurring_billing\snrb\apps'

for app in apps:
    app_dir = os.path.join(base_dir, app)
    os.makedirs(app_dir, exist_ok=True)
    
    with open(os.path.join(app_dir, '__init__.py'), 'w') as f:
        pass
        
    with open(os.path.join(app_dir, 'apps.py'), 'w') as f:
        f.write(f'''from django.apps import AppConfig\n\nclass {app.capitalize()}Config(AppConfig):\n    default_auto_field = "django.db.models.BigAutoField"\n    name = "apps.{app}"\n''')
        
    with open(os.path.join(app_dir, 'models.py'), 'w') as f:
        f.write('# Models to be defined in Phase 2+\n')
        
    if app not in ['notifications', 'core']:
        with open(os.path.join(app_dir, 'urls.py'), 'w') as f:
            f.write('from django.urls import path\n\nurlpatterns = []\n')

# Delete old settings.py
old_settings = r'C:\Users\Pedro Lucas\Documents\Estudos\Python\DRF\scheduling_and_recurring_billing\snrb\snrb\settings.py'
if os.path.exists(old_settings):
    os.remove(old_settings)

print('Apps created and old settings deleted!')
