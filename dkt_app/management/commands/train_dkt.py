import os
import torch
from django.core.management.base import BaseCommand

# Import your DKT related utilities and models
from dkt_app.dkt_utils import Data_Loader, train
from IntelligentHomeworkGradingSystem.settings import BASE_DIR


class Command(BaseCommand):
    help = 'Trains the DKT model and saves the trained model.'

    def handle(self, *args, **options):
        # 加载data_st,knowledge_n
        self.stdout.write(self.style.SUCCESS('Starting DKT model training...'))
        self.stdout.write('Loading data from Django models...')
        data_loader = Data_Loader()
        data_st = data_loader.data_st
        knowledge_n = data_loader.knowledge_dim

        # except data_st
        if not data_st:
            self.stdout.write(self.style.WARNING('No student submission data found. Aborting training.'))
            return

        self.stdout.write(f'Data loaded. Found {len(data_st)} students and {knowledge_n} knowledge points.')

        # 2. Define training options
        opts = {
            'knowledge_n': knowledge_n,
            'epoch_n': 10,  # You can adjust the number of epochs
        }

        # 3. Train the DKT model
        self.stdout.write('Training DKT model...')
        H, score_all, trained_model = train(data_st, opts)
        self.stdout.write(self.style.SUCCESS('DKT model training completed.'))

        # 4. Save the trained model
        model_save_dir = os.path.join(BASE_DIR, 'dkt_app', 'trained_models')
        os.makedirs(model_save_dir, exist_ok=True)
        model_path = os.path.join(model_save_dir, 'dkt_model.pth')

        torch.save(trained_model.state_dict(), model_path)
        self.stdout.write(self.style.SUCCESS(f'Trained DKT model saved to: {model_path}'))

        self.stdout.write(self.style.SUCCESS('DKT training job finished successfully.'))


