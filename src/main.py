#!/usr/bin/env python3
"""
Translate IDML - Applicazione CLI per tradurre file InDesign IDML
"""

import os
import sys
from pathlib import Path
from typing import Optional
import asyncio
import logging

import click
from dotenv import load_dotenv

from idml_processor import IDMLProcessor
from text_extractor import TextExtractor
from translator import Translator
from domain_translator import DomainAwareTranslator
from document_analyzer import DocumentAnalyzer
from context_detector import DocumentContextDetector
from async_translator import AsyncTranslator
from translation_memory import TranslationMemory
from consistency_checker import ConsistencyChecker
from enhanced_post_processor import EnhancedTranslationPostProcessor


# Carica variabili d'ambiente
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _detect_domain_from_filename(filename: str) -> str:
    """Rileva automaticamente il dominio dal nome del file"""
    filename_lower = filename.lower()
    
    safety_keywords = ['safeguard', 'safety', 'sicurezza', 'anticaduta', 'protezione']
    construction_keywords = ['skyfix', 'riwega', 'dach', 'roof', 'tetto', 'construction']
    
    if any(keyword in filename_lower for keyword in safety_keywords):
        return 'safety'
    elif any(keyword in filename_lower for keyword in construction_keywords):
        return 'construction'
    
    return 'technical'  # Default


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
              help='Contesto specifico del documento (es: "Installation manual for fall protection systems")')
@click.option('--auto-context', is_flag=True, default=True,
              help='Rileva automaticamente il contesto del documento (default: attivo)')
@click.option('--context-template', 
              type=click.Choice(['safety_manual', 'construction_manual', 'technical_specification', 'marketing_brochure']),
              help='Usa template di contesto predefinito')
@click.option('--preview', is_flag=True,
              help='Mostra anteprima e statistiche senza tradurre')
@click.option('--estimate-cost', is_flag=True,
              help='Stima il costo della traduzione')
@click.option('--verbose', '-v', is_flag=True,
              help='Output verboso')
@click.option('--use-cache', is_flag=True, default=True,
              help='Usa Translation Memory per velocizzare traduzioni (default: attivo)')
@click.option('--update-tm', is_flag=True, default=True,
              help='Aggiorna Translation Memory con nuove traduzioni (default: attivo)')
@click.option('--check-consistency', is_flag=True, default=True,
              help='Verifica consistenza delle traduzioni (default: attivo)')
@click.option('--async-mode', is_flag=True, default=True,
              help='Usa traduzione asincrona per performance migliori (default: attivo)')
@click.option('--max-concurrent', type=int, default=5,
              help='Numero massimo di richieste API concorrenti (default: 5)')
@click.option('--post-process', is_flag=True, default=True,
              help='Applica correzioni automatiche post-traduzione (default: attivo)')
@click.option('--prevent-overflow', is_flag=True, default=False,
              help='Attiva prevenzione overflow testo per InDesign')
@click.option('--max-expansion', type=int, default=None,
              help='Percentuale massima espansione testo (es: 30 per tedesco)')
@click.option('--compression-mode', type=click.Choice(['normal', 'compact', 'ultra_compact']),
              default='normal', help='Modalità compressione per overflow prevention')
@click.option('--overflow-report', is_flag=True, default=False,
              help='Genera report dettagliato rischi overflow')
def main(input_file: Path, output: Optional[Path], target_lang: str, 
         source_lang: Optional[str], api_key: str, model: str,
         context: Optional[str], auto_context: bool, context_template: Optional[str],
         preview: bool, estimate_cost: bool, verbose: bool,
         use_cache: bool, update_tm: bool, check_consistency: bool,
         async_mode: bool, max_concurrent: int, post_process: bool,
         prevent_overflow: bool, max_expansion: Optional[int],
         compression_mode: str, overflow_report: bool):
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
    
    # Auto-detect domain dal nome file
    detected_domain = _detect_domain_from_filename(input_file.name)
    
    # Setup output file se non specificato
    if not output:
        output = input_file.with_stem(f"{input_file.stem}_{target_lang}")
    
    if verbose:
        click.echo(f"📁 File input: {input_file}")
        click.echo(f"📁 File output: {output}")
        click.echo(f"🌍 Lingua target: {target_lang}")
        if source_lang:
            click.echo(f"🌍 Lingua source: {source_lang}")
        click.echo(f"🤖 Modello: {model}")
        click.echo(f"🎯 Dominio rilevato: {detected_domain}")
        click.echo(f"⚡ Modalità: {'Asincrona' if async_mode else 'Sincrona'}")
        click.echo(f"💾 Cache TM: {'Attiva' if use_cache else 'Disattiva'}")
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
        
        # 1b. Validazione font per lingue non latine
        font_validation = processor.validate_font_compatibility(target_lang)
        if font_validation['requires_special_fonts'] and font_validation['warnings']:
            if not click.confirm("\n⚠️  Trovati potenziali problemi di compatibilità font. Continuare comunque?"):
                click.echo("Traduzione annullata.")
                sys.exit(1)
        
        # 1c. Controllo grafiche collegate con possibile testo
        linked_graphics_check = processor.check_linked_graphics_text()
        if linked_graphics_check['potential_text_graphics'] and verbose:
            click.echo("\n📌 Nota: alcune grafiche collegate potrebbero contenere testo da tradurre separatamente.")
        
        # 1d. Analisi consistenza stili (per validazione post-traduzione)
        original_style_analysis = processor.analyze_style_consistency()
        
        # 2. ANALISI PRELIMINARE DEL DOCUMENTO
        if verbose:
            click.echo("🔍 Analisi preliminare documento...")
        
        analyzer = DocumentAnalyzer()
        doc_analysis = analyzer.analyze_document(processor.stories_data, processor.get_document_info())
        
        if verbose:
            click.echo(analyzer.get_analysis_summary())
        
        # 3. Estrai il testo con contesto migliorato
        if verbose:
            click.echo("📝 Estrazione testo con analisi...")
        
        # Usa extractor con glossario del progetto e domain awareness
        project_path = str(input_file.parent)
        extractor = TextExtractor(project_path=project_path)
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
        
        # 4. Integrazione contesto da analisi
        document_context = doc_analysis['translation_context']
        context_info = {
            'type': doc_analysis['document_type'],
            'domain': doc_analysis['domain'],
            'complexity': doc_analysis['quality_indicators']['complexity_score']
        }
        
        if auto_context or context_template:
            if verbose:
                click.echo("🔍 Integrazione contesto avanzato...")
            
            context_detector = DocumentContextDetector()
            
            if context_template:
                # Usa template predefinito
                document_context = context_template
                context_info = context_detector.context_templates.get(context_template, {})
                if verbose:
                    click.echo(f"   Template utilizzato: {context_template}")
            elif auto_context:
                # Rilevamento automatico
                document_context, confidence, context_info = context_detector.detect_context(text_segments)
                if verbose:
                    click.echo(f"   Contesto rilevato: {document_context} (confidenza: {confidence:.2f})")
                    if confidence > 0.3:
                        click.echo(f"   Tipo: {context_info.get('description', 'N/A')}")
        
        # Crea contesto finale per traduzione
        final_context = context
        if document_context and document_context != 'generic':
            context_prompt = context_detector.create_context_prompt(document_context, context_info, context)
            if not context:  # Solo se non è stato fornito un contesto manuale
                final_context = context_prompt
            elif verbose:
                click.echo(f"📋 Contesto rilevato disponibile: {context_prompt}")
        
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
                if async_mode:
                    # Usa translator normale per stima
                    temp_translator = Translator(api_key, model)
                    cost_estimate = temp_translator.estimate_cost(texts_to_translate, target_lang)
                else:
                    translator = Translator(api_key, model)
                    cost_estimate = translator.estimate_cost(texts_to_translate, target_lang)
                
                click.echo(f"\n💰 Stima costi:")
                click.echo(f"   Token input stimati: {cost_estimate['estimated_input_tokens']:,}")
                click.echo(f"   Token output stimati: {cost_estimate['estimated_output_tokens']:,}")
                click.echo(f"   Costo stimato: ${cost_estimate['estimated_total_cost_usd']:.4f} USD")
                
                if estimate_cost:
                    return
        
        # 4. Traduci
        if verbose:
            click.echo(f"\n🌍 Avvio traduzione in {target_lang}...")
            
        if async_mode:
            # Usa traduttore asincrono
            if verbose:
                click.echo("   Modalità asincrona attiva - traduzioni parallele")
                
            # Esegui traduzione asincrona
            async def async_translate():
                async with AsyncTranslator(
                    api_key, model, max_concurrent, use_cache
                ) as translator:
                    return await translator.translate_texts_batch(
                        texts_to_translate, target_lang, source_lang, 
                        final_context, document_context
                    )
                    
            translated_texts = asyncio.run(async_translate())
            
            # Ottieni statistiche
            async def get_stats():
                async with AsyncTranslator(
                    api_key, model, max_concurrent, use_cache
                ) as translator:
                    return translator.get_statistics()
                    
            async_stats = asyncio.run(get_stats())
            
            if verbose and async_stats:
                click.echo(f"\n📈 Statistiche traduzione:")
                click.echo(f"   Cache hits: {async_stats['cache_hits']}")
                click.echo(f"   API calls: {async_stats['api_calls']}")
                click.echo(f"   Tempo totale: {async_stats['total_time']:.2f}s")
                if async_stats['cache_hits'] > 0:
                    click.echo(f"   Cache hit rate: {async_stats['cache_hit_rate']:.1%}")
                    
        else:
            # USA DOMAIN-AWARE TRANSLATOR con analisi documento
            domain_from_analysis = doc_analysis.get('domain', detected_domain)
            domain_translator = DomainAwareTranslator(
                api_key, model, project_path, domain_from_analysis
            )
            
            # Mostra info dominio se verbose
            if verbose:
                domain_info = domain_translator.get_domain_info()
                click.echo(f"   🎯 Dominio analizzato: {domain_from_analysis}")
                click.echo(f"   🔒 Termini protetti: {domain_info['protected_terms_count']}")
                click.echo(f"   🎨 Complessità: {doc_analysis['quality_indicators']['complexity_score']:.2f}")
            
            # Usa contesto migliorato dall'analisi
            enhanced_context = document_context or final_context
            
            # Analizza frame per overflow prevention se richiesto
            frame_metrics = None
            if prevent_overflow:
                if verbose:
                    click.echo("🔍 Analisi text frame per overflow prevention...")
                frame_analysis = processor.analyze_text_frames()
                frame_metrics = frame_analysis.get('frames', {})
                if verbose:
                    click.echo(f"   📐 Trovati {frame_analysis.get('total_frames', 0)} text frame")
            
            translated_texts = domain_translator.translate_texts(
                texts_to_translate, 
                target_lang, 
                source_lang, 
                enhanced_context,
                frame_metrics=frame_metrics,
                prevent_overflow=prevent_overflow
            )
        
        if verbose:
            click.echo(f"✅ Traduzione completata ({len(translated_texts)} testi)")
        
        # 5. Post-processing avanzato per correzioni automatiche
        if post_process:
            if verbose:
                click.echo("🔧 Applicazione correzioni avanzate post-traduzione...")
                
            enhanced_processor = EnhancedTranslationPostProcessor()
            original_translations = translated_texts.copy()
            # Backup traduzioni originali per report
            original_translations = translated_texts.copy()
            
            translated_texts = enhanced_processor.process_translations(translated_texts, target_lang)
            
            # Report qualità avanzato
            if verbose:
                quality_report = enhanced_processor.generate_enhanced_quality_report(
                    original_translations, translated_texts, target_lang
                )
                
                click.echo(f"📊 Report Qualità:")
                if 'consistency_score' in quality_report:
                    click.echo(f"   Punteggio consistenza: {quality_report['consistency_score']:.2f}/1.00")
                
                click.echo(f"   Qualità finale: {quality_report.get('corrected_quality', 0):.1%}")
                if quality_report.get('corrections_applied', 0) > 0:
                    click.echo(f"   Correzioni applicate: {quality_report['corrections_applied']}")
                
                # Mostra raccomandazioni se presenti
                if quality_report.get('recommendations'):
                    click.echo("💡 Raccomandazioni:")
                    for rec in quality_report['recommendations'][:3]:
                        click.echo(f"   - {rec}")
        elif verbose:
            click.echo("ℹ️  Post-processing disabilitato")
        
        # 5b. Overflow prevention post-processing se richiesto
        if prevent_overflow and post_process:
            if verbose:
                click.echo("📏 Applicazione correzioni overflow prevention...")
            
            # Calcola lunghezze massime basate su espansione
            expansion_factor = max_expansion if max_expansion else {
                'de': 30, 'en': 10, 'fr': 15, 'es': 5, 'pt': 10
            }.get(target_lang, 20)
            
            max_lengths = []
            for original, translated in zip(texts_to_translate, translated_texts):
                max_len = int(len(original) * (1 + expansion_factor / 100))
                max_lengths.append(max_len)
            
            # Applica correzioni overflow
            enhanced_processor = enhanced_processor if post_process else EnhancedTranslationPostProcessor()
            translated_texts = enhanced_processor.apply_overflow_corrections(
                translated_texts, max_lengths, target_lang
            )
            
            if verbose:
                click.echo(f"   ✅ Correzioni overflow applicate con espansione max {expansion_factor}%")
        
        # 6. Verifica consistenza se richiesto
        if check_consistency:
            if verbose:
                click.echo("🔍 Verifica consistenza traduzioni...")
                
            checker = ConsistencyChecker(TranslationMemory() if use_cache else None)
            
            # Verifica traduzioni
            issues = checker.check_translations(
                texts_to_translate, translated_texts, target_lang, source_lang
            )
            
            # Applica correzioni automatiche
            translated_texts = checker.apply_consistency_rules(translated_texts, target_lang)
            
            if issues and verbose:
                click.echo(f"   Trovate {len(issues)} possibili inconsistenze")
                report = checker.generate_report()
                click.echo("\n" + report)
        
        # 7. Mappa traduzioni ai segmenti
        story_translations = extractor.map_translations_to_segments(
            text_segments, translated_texts
        )
        
        # 7a. MASTER PAGES TRANSLATION
        if verbose:
            click.echo("📋 Traduzione Master Pages...")
        
        master_content = processor.extract_master_pages_content()
        if master_content:
            # Estrai testi traducibili dalle master pages
            master_texts_to_translate = []
            master_file_mapping = {}
            
            for master_file, master_data in master_content.items():
                translatable_texts = master_data.get('translatable_texts', [])
                if translatable_texts:
                    master_file_texts = []
                    for text_info in translatable_texts:
                        master_file_texts.append(text_info['content'])
                        master_texts_to_translate.append(text_info['content'])
                    master_file_mapping[master_file] = master_file_texts
            
            if master_texts_to_translate:
                if verbose:
                    click.echo(f"   📄 Trovati {len(master_texts_to_translate)} testi in master pages")
                
                # Traduci testi master pages
                if async_mode:
                    # Usa traduttore asincrono per master pages
                    async def async_translate_masters():
                        async with AsyncTranslator(
                            api_key, model, max_concurrent, use_cache
                        ) as translator:
                            return await translator.translate_texts_batch(
                                master_texts_to_translate, target_lang, source_lang, 
                                final_context, document_context
                            )
                    master_translations = asyncio.run(async_translate_masters())
                else:
                    # Usa domain translator anche per master pages
                    master_translations = domain_translator.translate_texts(
                        master_texts_to_translate, 
                        target_lang, 
                        source_lang, 
                        enhanced_context
                    )
                
                # Post-process master page translations
                if post_process:
                    enhanced_processor = enhanced_processor if 'enhanced_processor' in locals() else EnhancedTranslationPostProcessor()
                    master_translations = enhanced_processor.process_translations(master_translations, target_lang)
                
                # Mappa traduzioni master pages per file
                master_translations_by_file = {}
                translation_index = 0
                
                for master_file, original_texts in master_file_mapping.items():
                    file_translations = []
                    for _ in original_texts:
                        if translation_index < len(master_translations):
                            file_translations.append(master_translations[translation_index])
                            translation_index += 1
                    master_translations_by_file[master_file] = file_translations
                
                # Aggiorna master pages nel documento
                updated = processor.update_master_pages(master_translations_by_file)
                if verbose:
                    if updated:
                        click.echo(f"   ✅ Master pages aggiornate con traduzioni")
                    else:
                        click.echo(f"   ⚠️ Nessuna master page aggiornata")
            else:
                if verbose:
                    click.echo("   ℹ️ Nessun testo traducibile trovato nelle master pages")
        else:
            if verbose:
                click.echo("   ℹ️ Nessuna master page trovata nel documento")
        
        # 7b. Genera report overflow se richiesto
        if overflow_report and prevent_overflow:
            if verbose:
                click.echo("📊 Generazione report overflow...")
            
            from overflow_detector import OverflowDetector
            detector = OverflowDetector()
            
            # Usa frame metrics gia' analizzati
            predictions = detector.predict_translation_overflow(
                texts_to_translate, target_lang, frame_metrics or {}
            )
            
            report = detector.generate_overflow_report(predictions, target_lang)
            
            click.echo("\n📄 REPORT OVERFLOW PREVENTION:")
            click.echo(f"   Rischio medio: {report['summary']['average_overflow_risk']:.2f}")
            click.echo(f"   Espansione stimata: {report['summary']['estimated_expansion']}%")
            click.echo("\n   Distribuzione rischi:")
            for risk_level, count in report['risk_distribution'].items():
                percentage = report['risk_percentages'][risk_level]
                click.echo(f"   - {risk_level}: {count} ({percentage}%)")
            
            if report['high_risk_texts']:
                click.echo("\n   ⚠️ Testi ad alto rischio:")
                for i, high_risk in enumerate(report['high_risk_texts'][:5], 1):
                    click.echo(f"   {i}. {high_risk['text_preview']}")
                    click.echo(f"      Rischio: {high_risk['overflow_risk']}")
                    click.echo(f"      Spazio: {high_risk['available_space']} car.")
            
            click.echo("\n   💡 Raccomandazioni:")
            for rec in report['recommendations']:
                click.echo(f"   - {rec}")
        
        # 8. Sostituisci nel documento
        if verbose:
            click.echo("🔄 Applicazione traduzioni al documento...")
        
        processor.replace_text_content(story_translations, target_lang)
        
        # 9. Salva file tradotto
        if verbose:
            click.echo(f"💾 Salvataggio in {output}...")
        
        processor.save_translated_idml(str(output))
        
        # 9a. Validazione post-traduzione
        if verbose:
            click.echo("🔍 Validazione documento tradotto...")
        
        # Ricarica il documento tradotto per validazione
        translated_processor = IDMLProcessor(str(output))
        translated_processor.load_idml()
        
        # Validazione integrità XML
        xml_validation = translated_processor.validate_xml_tag_integrity()
        
        # Validazione consistenza stili se richiesta
        if check_consistency:
            translated_style_analysis = translated_processor.analyze_style_consistency()
            style_validation = processor.validate_style_preservation(original_style_analysis, translated_style_analysis)
            
            if not style_validation['is_valid'] and style_validation['discrepancies']:
                click.echo("⚠️  Trovate discrepanze negli stili dopo la traduzione")
                if verbose:
                    for discrepancy in style_validation['discrepancies'][:3]:
                        click.echo(f"   - {discrepancy}")
        
        # Genera warning se ci sono errori critici
        if not xml_validation['is_valid']:
            click.echo("⚠️  Trovati problemi di integrità XML - verificare il documento in InDesign")
        
        # 9b. Genera checklist DTP
        dtp_checklist = processor.generate_dtp_checklist(
            target_lang, stats, font_validation, xml_validation, linked_graphics_check
        )
        processor.print_dtp_checklist(dtp_checklist)
        
        success_msg = f"🎉 Traduzione completata!\n   File salvato: {output}"
        if detected_domain != 'technical':
            success_msg += f"\n   🎯 Dominio: {detected_domain}"
        
        click.echo(success_msg)
        
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
        
        # Estrai testo per statistiche con glossario
        extractor = TextExtractor(project_path=str(input_file.parent))
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


@cli.command()
@click.argument('input_files', nargs=-1, required=True, type=click.Path(exists=True, path_type=Path))
@click.option('--target-lang', '-t', required=True,
              help='Lingua di destinazione per tutte le traduzioni')
@click.option('--output-dir', '-d', type=click.Path(path_type=Path),
              help='Directory di output (default: stessa directory dei file)')
@click.option('--api-key', envvar='OPENAI_API_KEY',
              help='Chiave API OpenAI')
@click.option('--model', default='gpt-3.5-turbo',
              help='Modello OpenAI da utilizzare')
@click.option('--use-cache', is_flag=True, default=True,
              help='Usa Translation Memory condivisa')
@click.option('--check-consistency', is_flag=True, default=True,
              help='Verifica consistenza tra documenti')
@click.option('--verbose', '-v', is_flag=True,
              help='Output verboso')
@click.option('--prevent-overflow', is_flag=True, default=False,
              help='Attiva prevenzione overflow testo per InDesign')
@click.option('--max-expansion', type=int, default=None,
              help='Percentuale massima espansione testo (es: 30 per tedesco)')
@click.option('--compression-mode', type=click.Choice(['normal', 'compact', 'ultra_compact']),
              default='normal', help='Modalità compressione per overflow prevention')
def batch(input_files: tuple, target_lang: str, output_dir: Optional[Path],
          api_key: str, model: str, use_cache: bool, 
          check_consistency: bool, verbose: bool, prevent_overflow: bool,
          max_expansion: Optional[int], compression_mode: str):
    """Traduce più file IDML in batch con consistenza garantita"""
    
    if not api_key:
        click.echo("Errore: Chiave API OpenAI richiesta per batch", err=True)
        sys.exit(1)
        
    # Filtra solo file IDML
    idml_files = [f for f in input_files if f.suffix.lower() == '.idml']
    
    if not idml_files:
        click.echo("Errore: Nessun file .idml trovato", err=True)
        sys.exit(1)
        
    click.echo(f"🗂️  Elaborazione batch di {len(idml_files)} file IDML")
    
    # Usa TM condivisa per tutto il batch
    tm = TranslationMemory() if use_cache else None
    
    # Raccogli tutti i testi per costruire contesto
    all_segments = []
    file_segments = {}
    
    if verbose:
        click.echo("\n📚 Analisi documenti...")
        
    for idml_file in idml_files:
        try:
            processor = IDMLProcessor(str(idml_file))
            processor.load_idml()
            
            extractor = TextExtractor(project_path=str(idml_file.parent))
            segments = extractor.extract_translatable_text(processor.stories_data)
            
            file_segments[idml_file] = segments
            all_segments.extend(segments)
            
            processor.close()
            
        except Exception as e:
            click.echo(f"⚠️  Errore analisi {idml_file}: {e}", err=True)
            
    # Rileva contesto globale
    context_detector = DocumentContextDetector()
    global_context, confidence, context_info = context_detector.detect_context(all_segments)
    
    if verbose:
        click.echo(f"\n📋 Contesto globale: {global_context} (confidenza: {confidence:.2f})")
        
    # Traduci ogni file
    success_count = 0
    
    for idml_file in idml_files:
        click.echo(f"\n🔄 Traduzione {idml_file.name}...")
        
        # Determina output
        if output_dir:
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / f"{idml_file.stem}_{target_lang}.idml"
        else:
            output_path = idml_file.with_stem(f"{idml_file.stem}_{target_lang}")
            
        try:
            # Usa il comando main con TM condivisa
            ctx = click.Context(main)
            ctx.invoke(main,
                      input_file=idml_file,
                      output=output_path,
                      target_lang=target_lang,
                      api_key=api_key,
                      model=model,
                      context_template=global_context if global_context != 'generic' else None,
                      use_cache=use_cache,
                      check_consistency=check_consistency,
                      verbose=False,
                      context=None,
                      auto_context=True,
                      preview=False,
                      estimate_cost=False,
                      update_tm=True,
                      async_mode=True,
                      max_concurrent=5,
                      source_lang=None,
                      post_process=True,
                      prevent_overflow=prevent_overflow,
                      max_expansion=max_expansion,
                      compression_mode=compression_mode,
                      overflow_report=False)
            
            success_count += 1
            click.echo(f"   ✅ Salvato: {output_path}")
            
        except Exception as e:
            click.echo(f"   ❌ Errore: {e}", err=True)
            
    # Report finale
    click.echo(f"\n📊 Batch completato: {success_count}/{len(idml_files)} file tradotti")
    
    if tm:
        stats = tm.get_statistics()
        click.echo(f"\n📈 Statistiche Translation Memory:")
        click.echo(f"   Traduzioni totali: {stats['total_translations']}")
        click.echo(f"   Termini: {stats['total_terms']}")
        
        tm.close()


@cli.command()
@click.option('--export', type=click.Path(), 
              help='Esporta TM in formato TMX')
@click.option('--source-lang', '-s', help='Lingua sorgente per export')
@click.option('--target-lang', '-t', help='Lingua target per export')
@click.option('--stats', is_flag=True, help='Mostra statistiche TM')
def tm(export: Optional[str], source_lang: Optional[str], 
       target_lang: Optional[str], stats: bool):
    """Gestisce la Translation Memory"""
    
    tm = TranslationMemory()
    
    if stats:
        tm_stats = tm.get_statistics()
        click.echo("📊 Statistiche Translation Memory:")
        click.echo(f"   Traduzioni totali: {tm_stats['total_translations']}")
        click.echo(f"   Termini salvati: {tm_stats['total_terms']}")
        click.echo(f"   Regole attive: {tm_stats['active_rules']}")
        
        if tm_stats['top_languages']:
            click.echo("\n🌍 Lingue più usate:")
            for lang, count in tm_stats['top_languages']:
                click.echo(f"   {lang}: {count} traduzioni")
                
        if tm_stats['most_used']:
            click.echo("\n🔁 Traduzioni più riutilizzate:")
            for trans in tm_stats['most_used'][:5]:
                src = trans['source_text'][:40] + '...' if len(trans['source_text']) > 40 else trans['source_text']
                click.echo(f"   '{src}' ({trans['usage_count']} usi)")
                
    if export:
        if not source_lang or not target_lang:
            click.echo("Errore: --source-lang e --target-lang richiesti per export", err=True)
            sys.exit(1)
            
        tm.export_tmx(export, source_lang, target_lang)
        click.echo(f"✅ TM esportata in: {export}")
        
    tm.close()


# Aggiungi i comandi al gruppo CLI
cli.add_command(main, name="translate")


if __name__ == '__main__':
    cli()