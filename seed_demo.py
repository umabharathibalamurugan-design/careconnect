import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from users.models import User
from societies.models import Society, Block, Flat
from residents.models import ResidentProfile
from guardians.models import Guardian
from volunteers.models import Volunteer
from security.models import SecurityGuard

society, _ = Society.objects.get_or_create(
    name='CareConnect Demo Society',
    defaults={'address':'CareConnect Demo Campus','city':'Chennai','pincode':'600001'},
)
block, _ = Block.objects.get_or_create(society=society, name='Tower A')
flat, _ = Flat.objects.get_or_create(block=block, flat_number='101')

def user(username, password, role, first='Demo', last='User'):
    obj, created = User.objects.get_or_create(username=username, defaults={
        'role': role, 'first_name': first, 'last_name': last, 'email': f'{username}@careconnect.local'
    })
    obj.role = role
    obj.first_name = first
    obj.last_name = last
    obj.set_password(password)
    obj.is_active = True
    obj.society = society
    obj.save()
    return obj

resident = user('resident_demo','CareConnect@123','resident','Demo','Resident')
ResidentProfile.objects.get_or_create(user=resident, defaults={'flat':flat,'is_owner':True})

guardian = user('guardian_demo','CareConnect@123','guardian','Demo','Guardian')
gp = ResidentProfile.objects.get_or_create(user=guardian, defaults={'flat':flat,'is_owner':False})[0]
Guardian.objects.get_or_create(user=guardian, resident=ResidentProfile.objects.get(user=resident), defaults={'relation':'Family','is_primary':True,'can_receive_alerts':True,'can_track_location':True})

volunteer = user('volunteer_demo','CareConnect@123','volunteer','Demo','Volunteer')
Volunteer.objects.get_or_create(user=volunteer, defaults={'society':society,'assigned_block':block,'available_for_emergency':True})

security_admin = user('security_admin_demo','CareConnect@123','security_admin','Demo','Security Admin')
SecurityGuard.objects.get_or_create(user=security_admin, defaults={'society':society,'gate_assigned':'Control Room','is_on_duty':True})
security = user('security_volunteer_demo','CareConnect@123','security_volunteer','Demo','Security Volunteer')
SecurityGuard.objects.get_or_create(user=security, defaults={'society':society,'gate_assigned':'Main Gate','is_on_duty':True})

admin = user('admin_demo','CareConnect@123','admin','Demo','Admin')
soc_admin = user('society_admin_demo','CareConnect@123','society_admin','Demo','Society Admin')
super_admin = user('superadmin_demo','CareConnect@123','superadmin','Demo','Super Admin')
print('Demo users ready:')
for x in ['admin_demo','society_admin_demo','superadmin_demo','resident_demo','guardian_demo','volunteer_demo','security_admin_demo','security_volunteer_demo']:
    print(x, '/ CareConnect@123')
