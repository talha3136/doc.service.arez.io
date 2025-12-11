class Config:
    SECRET_KEY = 'flask-insecure-change-me'
    DEBUG = True

    # AI settings
    AI_PROJECT = 'earnflex-frontier'
    AI_LOCATION = 'us-central1'
    GENERATIVE_AI_MODEL = 'gemini-2.0-flash-001'
    DOCUMENT_AI_PROJECT = 'earnflex-frontier'
    DOCUMENT_AI_LOCATION = 'us'
    DOCUMENT_AI_PROCESSOR_ID = '7e847b8bcb99bac3'

    # Multiple vector databases configuration
    VECTOR_DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'test-vector',
            'USER': 'postgres',
            'PASSWORD': 'NgTVaWi2wZ4jMUneUTGQ',
            'HOST': '34.105.252.203',
            'PORT': 5432,
        },
        'field_job': {
            'ENGINE': 'postgresql',
            'NAME': 'vector_db1',
            'USER': 'postgres',
            'PASSWORD': 'password',
            'HOST': 'localhost',
            'PORT': 5432,
        },
        

    }

    @staticmethod
    def get(config_name):
        configs = {
            'default': Config,
            'development': Config,
            'production': Config,  # Can extend for different environments
        }
        return configs.get(config_name, Config)