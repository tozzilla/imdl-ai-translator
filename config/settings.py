"""
Configurazioni globali per l'applicazione Translate IDML
"""

import os
from pathlib import Path
from typing import Dict, Any


# Directory base del progetto
BASE_DIR = Path(__file__).parent.parent


# Configurazioni OpenAI
OPENAI_CONFIG = {
    'default_model': 'gpt-3.5-turbo',
    'alternative_models': [
        'gpt-4',
        'gpt-4-turbo-preview',
        'gpt-3.5-turbo-16k'
    ],
    'max_tokens_per_request': 3000,
    'rate_limit_delay': 1.0,  # secondi
    'max_retries': 3,
    'temperature': 0.3  # Per traduzioni coerenti
}


# Configurazioni traduzione
TRANSLATION_CONFIG = {
    'batch_size_chars': 10000,  # Dimensione massima batch in caratteri
    'preserve_formatting': True,
    'preserve_special_chars': True,
    'min_text_length': 2,  # Lunghezza minima testo da tradurre
    'exclude_patterns': [
        r'^\d+$',  # Solo numeri
        r'^[^\w\s]+$',  # Solo punteggiatura
        r'^[A-Z0-9_]+$',  # Codici/ID
        r'https?://',  # URL
        r'www\.',  # URL
        r'@.*\.',  # Email
        r'.*@.*'  # Email
    ]
}


# Lingue supportate con nomi completi
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'it': 'Italian', 
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'ja': 'Japanese',
    'ko': 'Korean',
    'zh': 'Chinese (Simplified)',
    'zh-tw': 'Chinese (Traditional)',
    'ar': 'Arabic',
    'hi': 'Hindi',
    'nl': 'Dutch',
    'sv': 'Swedish',
    'no': 'Norwegian',
    'da': 'Danish',
    'fi': 'Finnish',
    'pl': 'Polish',
    'cs': 'Czech',
    'hu': 'Hungarian',
    'ro': 'Romanian',
    'bg': 'Bulgarian',
    'hr': 'Croatian',
    'sk': 'Slovak',
    'sl': 'Slovenian',
    'et': 'Estonian',
    'lv': 'Latvian',
    'lt': 'Lithuanian',
    'mt': 'Maltese',
    'el': 'Greek',
    'tr': 'Turkish',
    'he': 'Hebrew',
    'th': 'Thai',
    'vi': 'Vietnamese',
    'uk': 'Ukrainian',
    'ca': 'Catalan',
    'eu': 'Basque',
    'gl': 'Galician'
}


# Configurazioni IDML
IDML_CONFIG = {
    'text_elements': [
        'Content',
        'Br',
        'CharacterStyleRange', 
        'ParagraphStyleRange'
    ],
    'preserve_attributes': [
        'AppliedCharacterStyle',
        'AppliedParagraphStyle',
        'FontStyle',
        'PointSize',
        'FillColor'
    ],
    'backup_originals': True,
    'temp_dir': BASE_DIR / 'temp'
}


# Configurazioni logging
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'log_file': BASE_DIR / 'logs' / 'translate_idml.log',
    'max_file_size': 10 * 1024 * 1024,  # 10MB
    'backup_count': 5
}


# Configurazioni costi (da aggiornare periodicamente)
COST_CONFIG = {
    'gpt-3.5-turbo': {
        'input_cost_per_1k_tokens': 0.0015,
        'output_cost_per_1k_tokens': 0.002
    },
    'gpt-4': {
        'input_cost_per_1k_tokens': 0.03,
        'output_cost_per_1k_tokens': 0.06
    },
    'gpt-4-turbo-preview': {
        'input_cost_per_1k_tokens': 0.01,
        'output_cost_per_1k_tokens': 0.03
    }
}


# Template prompt per diversi tipi di traduzione
PROMPT_TEMPLATES = {
    'standard': """Translate the following texts{source_lang} to {target_lang}.

IMPORTANT INSTRUCTIONS:
- Maintain the exact same format and structure
- Keep any special characters or formatting
- Preserve the tone and style of the original text
- Return exactly {count} translations, one per line
- Each translation should correspond to the input text at the same position
- Do not add explanations or additional text

{context_section}

TEXTS TO TRANSLATE:
{texts}

Provide {count} translations, numbered from 1 to {count}:""",

    'marketing': """Translate the following marketing/advertising texts{source_lang} to {target_lang}.

IMPORTANT INSTRUCTIONS:
- Maintain the persuasive tone and marketing impact
- Adapt cultural references if necessary while preserving meaning
- Keep brand names unchanged unless specified otherwise
- Preserve call-to-action strength
- Return exactly {count} translations, one per line
- Do not add explanations or additional text

{context_section}

TEXTS TO TRANSLATE:
{texts}

Provide {count} translations, numbered from 1 to {count}:""",

    'technical': """Translate the following technical texts{source_lang} to {target_lang}.

IMPORTANT INSTRUCTIONS:
- Maintain technical accuracy and precision
- Keep technical terms consistent
- Preserve any code, formulas, or technical specifications
- Use appropriate technical terminology for the target language
- Return exactly {count} translations, one per line
- Do not add explanations or additional text

{context_section}

TEXTS TO TRANSLATE:
{texts}

Provide {count} translations, numbered from 1 to {count}:"""
}


def get_config(section: str = None) -> Dict[str, Any]:
    """
    Ottiene configurazioni per una sezione specifica o tutte
    
    Args:
        section: Nome della sezione (es: 'openai', 'translation')
        
    Returns:
        Dizionario con le configurazioni
    """
    configs = {
        'openai': OPENAI_CONFIG,
        'translation': TRANSLATION_CONFIG,
        'languages': SUPPORTED_LANGUAGES,
        'idml': IDML_CONFIG,
        'logging': LOGGING_CONFIG,
        'costs': COST_CONFIG,
        'prompts': PROMPT_TEMPLATES
    }
    
    if section:
        return configs.get(section, {})
    
    return configs


def get_env_var(var_name: str, default: Any = None) -> Any:
    """
    Ottiene una variabile d'ambiente con valore di default
    
    Args:
        var_name: Nome della variabile d'ambiente
        default: Valore di default se la variabile non esiste
        
    Returns:
        Valore della variabile d'ambiente o default
    """
    return os.getenv(var_name, default)


def create_directories():
    """Crea le directory necessarie se non esistono"""
    directories = [
        IDML_CONFIG['temp_dir'],
        LOGGING_CONFIG['log_file'].parent,
        BASE_DIR / 'output',
        BASE_DIR / 'backup'
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


if __name__ == '__main__':
    # Test configurazioni
    print("🔧 Configurazioni Translate IDML:")
    print(f"   Base directory: {BASE_DIR}")
    print(f"   Modello OpenAI default: {OPENAI_CONFIG['default_model']}")
    print(f"   Lingue supportate: {len(SUPPORTED_LANGUAGES)}")
    print(f"   Template prompt: {len(PROMPT_TEMPLATES)}")
    
    print("\n🌍 Prime 10 lingue supportate:")
    for i, (code, name) in enumerate(list(SUPPORTED_LANGUAGES.items())[:10]):
        print(f"   {code}: {name}")
    
    print(f"\n... e altre {len(SUPPORTED_LANGUAGES) - 10} lingue")