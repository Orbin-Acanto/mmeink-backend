from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from chat.models import (
    CustomerInfo, ChatSession, Message, CannedResponse
)
from analytics.models import ChatTag  # Import from analytics instead
from django.utils import timezone

User = get_user_model()

class Command(BaseCommand):
    help = 'Create test data for development'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Creating test data...'))
        
        # Create admin user
        if not User.objects.filter(email='acantoahmed67@gmail.com').exists():
            admin = User.objects.create_superuser(
                username='oacanto',
                email='acantoahmed67@gmail.com',
                password='115599',
                first_name='Orbin',
                last_name='Acanto',
                role='admin'
            )
            self.stdout.write(self.style.SUCCESS(f'✓ Created admin user: {admin.email}'))
        else:
            self.stdout.write(self.style.WARNING('Admin user already exists'))
        
        # Create agent users
        agents = []
        agent_data = [
            {'username': 'john_agent', 'email': 'john@mmeink.com', 'first_name': 'John', 'last_name': 'Smith'},
            {'username': 'sarah_agent', 'email': 'sarah@mmeink.com', 'first_name': 'Sarah', 'last_name': 'Johnson'},
            {'username': 'mike_agent', 'email': 'mike@mmeink.com', 'first_name': 'Mike', 'last_name': 'Williams'},
        ]
        
        for data in agent_data:
            if not User.objects.filter(email=data['email']).exists():
                agent = User.objects.create_user(
                    username=data['username'],
                    email=data['email'],
                    password='agent123',
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    role='agent',
                    status='online',
                    is_available=True
                )
                agents.append(agent)
                self.stdout.write(self.style.SUCCESS(f'✓ Created agent: {agent.email}'))
            else:
                agents.append(User.objects.get(email=data['email']))
                self.stdout.write(self.style.WARNING(f'Agent {data["email"]} already exists'))
        
        # Create customer info
        customers = []
        customer_data = [
            {'name': 'Alice Cooper', 'email': 'alice@example.com', 'phone': '+1234567890'},
            {'name': 'Bob Martin', 'email': 'bob@example.com', 'phone': '+1234567891'},
            {'name': 'Carol White', 'email': 'carol@example.com', 'phone': '+1234567892'},
            {'name': 'David Brown', 'email': 'david@example.com', 'phone': '+1234567893'},
            {'name': 'Eve Davis', 'email': 'eve@example.com', 'phone': '+1234567894'},
        ]
        
        for data in customer_data:
            customer, created = CustomerInfo.objects.get_or_create(
                email=data['email'],
                defaults={
                    'name': data['name'],
                    'phone': data['phone']
                }
            )
            customers.append(customer)
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Created customer: {customer.name}'))
        
        # Create chat sessions with different statuses
        if agents and customers:
            session_configs = [
                {'status': 'bot', 'customer': customers[0]},
                {'status': 'waiting', 'customer': customers[1]},
                {'status': 'active', 'customer': customers[2], 'agent': agents[0]},
                {'status': 'closed', 'customer': customers[3], 'agent': agents[1]},
                {'status': 'abandoned', 'customer': customers[4]},
            ]
            
            for config in session_configs:
                # Check if session already exists
                existing = ChatSession.objects.filter(
                    customer_email=config['customer'].email,
                    status=config['status']
                ).first()
                
                if not existing:
                    session = ChatSession.objects.create(
                        customer=config['customer'],
                        customer_name=config['customer'].name,
                        customer_email=config['customer'].email,
                        customer_phone=config['customer'].phone,
                        status=config['status'],
                        assigned_agent=config.get('agent'),
                        user_ip='192.168.1.1',
                        user_agent='Mozilla/5.0...'
                    )
                    
                    # Update message count
                    session.message_count = 0
                    
                    # Create some messages for each session
                    Message.objects.create(
                        session=session,
                        sender_type='customer',
                        sender_name=config['customer'].name,
                        message='Hello, I need help with my order.',
                    )
                    session.message_count += 1
                    
                    if config['status'] in ['active', 'closed']:
                        Message.objects.create(
                            session=session,
                            sender_type='agent',
                            sender_name=config['agent'].get_full_name(),
                            sender=config['agent'],
                            message='Hi! I\'d be happy to help you with that.',
                        )
                        session.message_count += 1
                        
                        Message.objects.create(
                            session=session,
                            sender_type='customer',
                            sender_name=config['customer'].name,
                            message='Great! Can you check order #12345?',
                        )
                        session.message_count += 1
                    
                    session.save()
                    self.stdout.write(self.style.SUCCESS(f'✓ Created {config["status"]} session for {config["customer"].name}'))
                else:
                    self.stdout.write(self.style.WARNING(f'Session already exists for {config["customer"].name} with status {config["status"]}'))
        
        # Create canned responses
        canned_responses = [
            {
                'title': 'Welcome Greeting',
                'category': 'greeting',
                'shortcut': '/hello',
                'message': 'Hello! Thank you for contacting us. How can I assist you today?',
                'is_global': True
            },
            {
                'title': 'Closing',
                'category': 'closing',
                'shortcut': '/bye',
                'message': 'Thank you for chatting with us today. If you need any further assistance, feel free to reach out. Have a great day!',
                'is_global': True
            },
            {
                'title': 'On Hold',
                'category': 'hold',
                'shortcut': '/hold',
                'message': 'I need to check on this for you. Please hold for a moment while I gather the information.',
                'is_global': True
            },
            {
                'title': 'Technical Issue',
                'category': 'common_issue',
                'shortcut': '/tech',
                'message': 'I understand you\'re experiencing a technical issue. Let me look into this for you.',
                'is_global': True
            },
        ]
        
        for data in canned_responses:
            response, created = CannedResponse.objects.get_or_create(
                shortcut=data['shortcut'],
                defaults=data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Created canned response: {response.title}'))
        
        # Create chat tags
        tags = [
            {'name': 'Technical Support', 'color': '#3B82F6'},
            {'name': 'Billing', 'color': '#10B981'},
            {'name': 'General Inquiry', 'color': '#6366F1'},
            {'name': 'Complaint', 'color': '#EF4444'},
            {'name': 'Feedback', 'color': '#F59E0B'},
        ]
        
        for data in tags:
            tag, created = ChatTag.objects.get_or_create(
                name=data['name'],
                defaults={'color': data['color']}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Created tag: {tag.name}'))
        
        self.stdout.write(self.style.SUCCESS('\n✅ Test data creation completed!'))
        self.stdout.write(self.style.WARNING('\n📝 Test Credentials:'))
        self.stdout.write(self.style.WARNING('━' * 50))
        self.stdout.write(self.style.WARNING('Admin Panel: http://127.0.0.1:8000/admin'))
        self.stdout.write(self.style.WARNING('━' * 50))
        self.stdout.write(self.style.SUCCESS('Admin User:'))
        self.stdout.write(self.style.WARNING('  Email: acantoahmed67@gmail.com'))
        self.stdout.write(self.style.WARNING('  Password: 115599'))
        self.stdout.write(self.style.WARNING('━' * 50))
        self.stdout.write(self.style.SUCCESS('Agent Users:'))
        self.stdout.write(self.style.WARNING('  Email: john@mmeink.com | Password: agent123'))
        self.stdout.write(self.style.WARNING('  Email: sarah@mmeink.com | Password: agent123'))
        self.stdout.write(self.style.WARNING('  Email: mike@mmeink.com | Password: agent123'))
        self.stdout.write(self.style.WARNING('━' * 50))