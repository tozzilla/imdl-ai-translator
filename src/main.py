#!/usr/bin/env python3
"""
Translate IDML - Applicazione CLI per tradurre file InDesign IDML
"""

import os
import sys
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv

from idml_processor import IDMLProcessor
from text_extractor import TextExtractor
from translator import Translator


# Carica variabili d'ambiente
load_dotenv()


@click.command()
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path), 
              help='File di output (default: aggiunge suffisso lingua al nome)')
@click.option('--target-lang', '-t', required=True, 
              help='Lingua di destinazione (es: en, it, es, fr)')
@click.option('--source-lang', '-s', 
              help='Lingua di origine (auto-detect se non specificata)')
@click.option('--api-key', envvar='OPENAI_API_KEY',
              help='Chiave API OpenAI (o usa variabile OPENAI_API_KEY)')
@click.option('--model', default='gpt-3.5-turbo',
              help='Modello OpenAI da utilizzare (default: gpt-3.5-turbo)')
@click.option('--context', 
              help='Contesto aggiuntivo per migliorare la traduzione')
@click.option('--preview', is_flag=True,
              help='Mostra anteprima e statistiche senza tradurre')
@click.option('--estimate-cost', is_flag=True,
              help='Stima il costo della traduzione')
@click.option('--verbose', '-v', is_flag=True,
              help='Output verboso')
def main(input_file: Path, output: Optional[Path], target_lang: str, 
         source_lang: Optional[str], api_key: str, model: str,
         context: Optional[str], preview: bool, estimate_cost: bool, verbose: bool):
    """
    Traduce il testo contenuto in un file IDML di InDesign.
    
    INPUT_FILE: Path al file IDML da tradurre
    """
    
    # Validazione parametri
    if not input_file.suffix.lower() == '.idml':
        click.echo("Errore: Il file di input deve essere un file .idml", err=True)
        sys.exit(1)
    
    if not preview and not estimate_cost and not api_key:
        click.echo("Errore: Chiave API OpenAI richiesta. Usa --api-key o imposta OPENAI_API_KEY", err=True)
        sys.exit(1)
    
    # Setup output file se non specificato
    if not output:
        output = input_file.with_stem(f"{input_file.stem}_{target_lang}")
    
    if verbose:
        click.echo(f"File input: {input_file}")
        click.echo(f"File output: {output}")
        click.echo(f"Lingua target: {target_lang}")
        if source_lang:
            click.echo(f"Lingua source: {source_lang}")
        click.echo(f"Modello: {model}")
        click.echo()
    
    try:
        # 1. Carica e processa il file IDML
        if verbose:
            click.echo("🔍 Caricamento file IDML...")
        
        processor = IDMLProcessor(str(input_file))
        processor.load_idml()
        
        doc_info = processor.get_document_info()
        if verbose:
            click.echo(f"   Documento: {doc_info['filename']}")
            click.echo(f"   Stories trovate: {doc_info['stories_count']}")
        
        # 2. Estrai il testo
        if verbose:
            click.echo("📝 Estrazione testo...")
        
        extractor = TextExtractor()
        text_segments = extractor.extract_translatable_text(processor.stories_data)
        
        if not text_segments:
            click.echo("❌ Nessun testo traducibile trovato nel file IDML")
            sys.exit(1)
        
        # Statistiche
        stats = extractor.get_translation_stats(text_segments)
        
        click.echo(f"📊 Statistiche:")
        click.echo(f"   Segmenti di testo: {stats['total_segments']}")
        click.echo(f"   Caratteri totali: {stats['total_characters']:,}")
        click.echo(f"   Parole totali: {stats['total_words']:,}")
        click.echo(f"   Stories coinvolte: {stats['stories_count']}")
        
        # Prepara testi per traduzione
        texts_to_translate = extractor.prepare_for_translation(text_segments)
        
        # Modalità preview
        if preview:
            click.echo(f"\n📋 Anteprima testi da tradurre:")
            for i, text in enumerate(texts_to_translate[:10], 1):  # Mostra primi 10
                click.echo(f"   {i}. {text[:80]}{'...' if len(text) > 80 else ''}")
            
            if len(texts_to_translate) > 10:
                click.echo(f"   ... e altri {len(texts_to_translate) - 10} testi")
            
            return
        
        # Stima costi
        if estimate_cost or verbose:
            if not api_key:
                click.echo("⚠️  Impossibile stimare costi senza chiave API")
            else:
                translator = Translator(api_key, model)
                cost_estimate = translator.estimate_cost(texts_to_translate, target_lang)
                
                click.echo(f"\n💰 Stima costi:")
                click.echo(f"   Token input stimati: {cost_estimate['estimated_input_tokens']:,}")
                click.echo(f"   Token output stimati: {cost_estimate['estimated_output_tokens']:,}")
                click.echo(f"   Costo stimato: ${cost_estimate['estimated_total_cost_usd']:.4f} USD")
                
                if estimate_cost:
                    return
        
        # 3. Traduci
        if verbose:
            click.echo(f"\n🌍 Avvio traduzione in {target_lang}...")
        
        translator = Translator(api_key, model)
        
        # Verifica lingua supportata
        supported_langs = translator.get_supported_languages()
        if target_lang not in supported_langs:
            click.echo(f"⚠️  Lingua '{target_lang}' non nell'elenco lingue note")
            click.echo(f"   Lingue supportate: {', '.join(supported_langs.keys())}")
            
            if not click.confirm("Continuare comunque?"):
                sys.exit(1)
        
        translated_texts = translator.translate_texts(
            texts_to_translate, 
            target_lang, 
            source_lang, 
            context
        )
        
        if verbose:
            click.echo(f"✅ Traduzione completata ({len(translated_texts)} testi)")
        
        # 4. Mappa traduzioni ai segmenti
        story_translations = extractor.map_translations_to_segments(
            text_segments, translated_texts
        )
        
        # 5. Sostituisci nel documento
        if verbose:
            click.echo("🔄 Applicazione traduzioni al documento...")
        
        processor.replace_text_content(story_translations)
        
        # 6. Salva file tradotto
        if verbose:
            click.echo(f"💾 Salvataggio in {output}...")
        
        processor.save_translated_idml(str(output))
        
        click.echo(f"🎉 Traduzione completata!")
        click.echo(f"   File salvato: {output}")
        
    except Exception as e:
        click.echo(f"❌ Errore: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    finally:
        # Cleanup
        if 'processor' in locals():
            processor.close()


@click.group()
def cli():
    """Translate IDML - Strumenti per tradurre file InDesign IDML"""
    pass


@cli.command()
def languages():
    """Mostra le lingue supportate"""
    translator = Translator("dummy_key")  # Non serve chiave valida per questo
    langs = translator.get_supported_languages()
    
    click.echo("🌍 Lingue supportate:")
    for code, name in sorted(langs.items()):
        click.echo(f"   {code:3} - {name}")


@cli.command()
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
def info(input_file: Path):
    """Mostra informazioni su un file IDML"""
    
    if not input_file.suffix.lower() == '.idml':
        click.echo("Errore: Il file deve essere un file .idml", err=True)
        sys.exit(1)
    
    try:
        processor = IDMLProcessor(str(input_file))
        processor.load_idml()
        
        doc_info = processor.get_document_info()
        
        click.echo(f"📄 Informazioni file IDML:")
        click.echo(f"   File: {doc_info['filename']}")
        click.echo(f"   Stories: {doc_info['stories_count']}")
        click.echo(f"   Nomi stories: {', '.join(doc_info['stories_names'])}")
        
        # Estrai testo per statistiche
        extractor = TextExtractor()
        text_segments = extractor.extract_translatable_text(processor.stories_data)
        
        if text_segments:
            stats = extractor.get_translation_stats(text_segments)
            click.echo(f"\n📊 Contenuto testuale:")
            click.echo(f"   Segmenti: {stats['total_segments']}")
            click.echo(f"   Caratteri: {stats['total_characters']:,}")
            click.echo(f"   Parole: {stats['total_words']:,}")
        else:
            click.echo(f"\n❌ Nessun testo traducibile trovato")
        
        processor.close()
        
    except Exception as e:
        click.echo(f"❌ Errore: {e}", err=True)
        sys.exit(1)


# Aggiungi i comandi al gruppo CLI
cli.add_command(main, name="translate")


if __name__ == '__main__':
    cli()