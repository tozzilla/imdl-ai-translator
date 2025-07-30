#!/usr/bin/env python3
"""
Main CLI per traduzione IDML con supporto modalità diagrammi
"""

import argparse
import sys
import os
from pathlib import Path

# Aggiungi src al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from idml_processor import IDMLProcessor
from text_extractor import TextExtractor
from overflow_detector import OverflowDetector
from overflow_manager import OverflowManager

def create_argument_parser():
    """Crea parser per argomenti CLI con supporto --diagram-mode"""
    parser = argparse.ArgumentParser(
        description='Traduce file IDML con gestione avanzata overflow per diagrammi',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  %(prog)s input.idml output.idml -l de
  %(prog)s input.idml output.idml -l de --diagram-mode
  %(prog)s input.idml output.idml -l de --overflow-prevention --max-compression 30
        """
    )
    
    # Argomenti principali
    parser.add_argument('input_file', help='File IDML da tradurre')
    parser.add_argument('output_file', help='File IDML tradotto di destinazione')
    parser.add_argument('-l', '--language', required=True, 
                       choices=['de', 'en', 'fr', 'es', 'it'],
                       help='Lingua di destinazione')
    
    # Opzioni overflow
    parser.add_argument('--overflow-prevention', action='store_true',
                       help='Attiva prevenzione overflow automatica')
    parser.add_argument('--max-compression', type=int, default=25, metavar='N',
                       help='Massima compressione testo in %% (default: 25)')
    
    # === NUOVA OPZIONE: DIAGRAM MODE ===
    parser.add_argument('--diagram-mode', action='store_true',
                       help='Attiva modalità specializzata per diagrammi e flowchart')
    parser.add_argument('--diagram-detection', action='store_true', default=True,
                       help='Attiva rilevamento automatico diagrammi (default: True)')
    parser.add_argument('--diagram-compression-level', 
                       choices=['moderate', 'aggressive', 'ultra'], default='aggressive',
                       help='Livello compressione per diagrammi (default: aggressive)')
    
    # Report e debug
    parser.add_argument('--generate-reports', action='store_true',
                       help='Genera report dettagliati su overflow e diagrammi')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Output verboso con dettagli operazioni')
    
    # Opzioni avanzate
    parser.add_argument('--font-size-reduction', type=float, default=0.9, metavar='FACTOR',
                       help='Fattore riduzione font size per overflow (default: 0.9)')
    parser.add_argument('--preserve-master-pages', action='store_true', default=True,
                       help='Preserva contenuto master pages (default: True)')
    
    return parser

def setup_logging(verbose: bool = False):
    """Configura logging per l'applicazione"""
    import logging
    
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(levelname)s: %(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    # Riduci verbosità di librerie esterne
    logging.getLogger('simple_idml').setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

def validate_inputs(args):
    """Valida argomenti di input"""
    # Verifica file input
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"❌ File input non trovato: {args.input_file}")
        return False
    
    if not input_path.suffix.lower() == '.idml':
        print(f"❌ File input deve essere .idml, trovato: {input_path.suffix}")
        return False
    
    # Verifica directory output
    output_path = Path(args.output_file)
    if not output_path.parent.exists():
        print(f"❌ Directory output non esiste: {output_path.parent}")
        return False
    
    # Validazione parametri
    if not (0.1 <= args.font_size_reduction <= 1.0):
        print(f"❌ font-size-reduction deve essere tra 0.1 e 1.0, trovato: {args.font_size_reduction}")
        return False
    
    if not (1 <= args.max_compression <= 80):
        print(f"❌ max-compression deve essere tra 1 e 80, trovato: {args.max_compression}")
        return False
    
    return True

def main():
    """Funzione principale CLI"""
    
    # Parse argomenti
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.verbose)
    
    # Valida inputs
    if not validate_inputs(args):
        sys.exit(1)
    
    print(f"🚀 Avvio traduzione IDML")
    print(f"   Input: {args.input_file}")
    print(f"   Output: {args.output_file}")
    print(f"   Lingua: {args.language}")
    
    if args.diagram_mode:
        print(f"   🎯 Modalità diagrammi attiva (livello: {args.diagram_compression_level})")
    
    if args.overflow_prevention:
        print(f"   🛡️  Prevenzione overflow attiva (max compression: {args.max_compression}%)")
    
    try:
        # === FASE 1: CARICAMENTO DOCUMENTO ===
        print(f"\n📖 Caricamento documento IDML...")
        processor = IDMLProcessor(args.input_file)
        processor.load_idml()
        
        doc_info = processor.get_document_info()
        logger.info(f"Documento caricato: {doc_info['stories_count']} stories")
        
        # === FASE 2: ESTRAZIONE TESTO ===
        print(f"\n✂️  Estrazione testo traducibile...")
        extractor = TextExtractor()
        segments = extractor.extract_translatable_text(processor.stories_data)
        
        stats = extractor.get_translation_stats(segments)
        print(f"   📊 Estratti {stats['total_segments']} segmenti")
        print(f"   📝 Totale: {stats['total_characters']} caratteri, {stats['total_words']} parole")
        
        # === FASE 3: ANALISI OVERFLOW (se richiesta) ===
        diagram_frames = {}
        overflow_predictions = []
        
        if args.overflow_prevention or args.diagram_mode:
            print(f"\n🔍 Analisi rischio overflow...")
            
            # Analizza frame del documento
            overflow_detector = OverflowDetector()
            frame_metrics = overflow_detector.analyze_document_frames(processor)
            
            if frame_metrics:
                print(f"   📐 Analizzati {len(frame_metrics)} text frame")
                
                # Predizione overflow per lingua destinazione
                texts_to_translate = [seg['original_text'] for seg in segments]
                overflow_predictions = overflow_detector.predict_translation_overflow(
                    texts_to_translate, args.language, frame_metrics
                )
                
                high_risk_count = sum(1 for p in overflow_predictions if p.overflow_risk > 1.2)
                print(f"   ⚠️  {high_risk_count} testi ad alto rischio overflow")
                
                # === RILEVAMENTO DIAGRAMMI (se attivo) ===
                if args.diagram_detection:
                    print(f"\n🎨 Rilevamento diagrammi automatico...")
                    diagram_frames = overflow_detector.detect_diagram_frames(
                        frame_metrics, processor.stories_data
                    )
                    
                    if diagram_frames:
                        critical_diagrams = sum(1 for info in diagram_frames.values() 
                                              if info['compression_priority'] == 'critical')
                        print(f"   🎯 Rilevati {len(diagram_frames)} frame diagramma")
                        print(f"   🚨 {critical_diagrams} diagrammi critici identificati")
                    else:
                        print(f"   ✅ Nessun diagramma problematico rilevato")
            else:
                print(f"   ⚠️  Impossibile analizzare frame - continuando senza prevenzione overflow")
        
        # === FASE 4: TRADUZIONE (simulata per questo esempio) ===
        print(f"\n🌐 Preparazione testi per traduzione...")
        texts_to_translate = extractor.prepare_for_translation(segments)
        
        # Qui normalmente chiameresti il servizio di traduzione
        # Per questo esempio, simula traduzioni con espansione del 30% per il tedesco
        if args.language == 'de':
            simulated_translations = [text + " (tradotto)" for text in texts_to_translate]
        else:
            simulated_translations = [f"{text} (translated)" for text in texts_to_translate]
        
        print(f"   ✅ {len(simulated_translations)} testi preparati per traduzione")
        
        # === FASE 5: GESTIONE OVERFLOW ===
        if overflow_predictions and (args.overflow_prevention or args.diagram_mode):
            print(f"\n🔧 Gestione overflow e compressione...")
            
            overflow_manager = OverflowManager()
            
            # Applica compressione specifica per diagrammi se necessario
            if diagram_frames and args.diagram_mode:
                print(f"   🎨 Applicazione compressione diagrammi...")
                processed_translations = overflow_manager.process_diagram_frames(
                    diagram_frames, simulated_translations
                )
                compression_applied = sum(1 for i, (orig, proc) in enumerate(zip(simulated_translations, processed_translations)) 
                                        if len(proc) < len(orig))
                print(f"   ✅ Compressione applicata a {compression_applied} testi diagramma")
                simulated_translations = processed_translations
            
            # Risolvi overflow restanti
            if any(p.overflow_risk > 1.0 for p in overflow_predictions):
                print(f"   🛠️  Risoluzione overflow con compressione standard...")
                resolutions = overflow_manager.resolve_overflow_predictions(overflow_predictions)
                
                successful_resolutions = sum(1 for r in resolutions if r.success)
                total_space_saved = sum(r.space_saved for r in resolutions)
                
                print(f"   ✅ {successful_resolutions}/{len(resolutions)} risoluzioni riuscite")
                print(f"   💾 Risparmiati {total_space_saved} caratteri totali")
        
        # === FASE 6: APPLICAZIONE TRADUZIONI ===
        print(f"\n📝 Applicazione traduzioni al documento...")
        
        # Mappa traduzioni ai segmenti
        story_translations = extractor.map_translations_to_segments(segments, simulated_translations)
        
        # Applica al documento
        processor.replace_text_content(story_translations, args.language)
        
        updated_stories = len(story_translations)
        print(f"   ✅ Aggiornate {updated_stories} stories con traduzioni")
        
        # === FASE 7: SALVATAGGIO ===
        print(f"\n💾 Salvataggio documento tradotto...")
        processor.save_translated_idml(args.output_file)
        
        # === FASE 8: REPORT FINALI ===
        if args.generate_reports:
            print(f"\n📊 Generazione report...")
            
            # Report overflow
            if overflow_predictions:
                overflow_report = overflow_detector.generate_overflow_report(
                    overflow_predictions, args.language
                )
                
                print(f"\n📈 REPORT OVERFLOW:")
                print(f"   Rischio medio: {overflow_report['summary']['average_overflow_risk']:.2f}")
                print(f"   Distribuzione rischi: {overflow_report['risk_percentages']}")
                
                # Salva report JSON
                import json
                report_file = Path(args.output_file).with_suffix('.overflow_report.json')
                with open(report_file, 'w', encoding='utf-8') as f:
                    json.dump(overflow_report, f, indent=2, ensure_ascii=False)
                print(f"   💾 Report overflow salvato: {report_file}")
            
            # Report diagrammi
            if diagram_frames:
                diagram_report = overflow_manager.generate_graphics_report(
                    diagram_frames, overflow_predictions
                )
                
                print(f"\n🎨 REPORT DIAGRAMMI:")
                print(f"   Totale grafiche: {diagram_report['summary']['total_graphics']}")
                print(f"   Rischio complessivo: {diagram_report['summary']['overall_risk']:.2f}")
                
                # Salva report JSON
                diagram_report_file = Path(args.output_file).with_suffix('.diagram_report.json')
                with open(diagram_report_file, 'w', encoding='utf-8') as f:
                    json.dump(diagram_report, f, indent=2, ensure_ascii=False)
                print(f"   💾 Report diagrammi salvato: {diagram_report_file}")
        
        # === COMPLETAMENTO ===
        print(f"\n🎉 Traduzione completata con successo!")
        print(f"   📄 File tradotto: {args.output_file}")
        
        if args.diagram_mode and diagram_frames:
            print(f"   🎯 Modalità diagrammi: {len(diagram_frames)} elementi processati")
        
        if args.overflow_prevention and overflow_predictions:
            high_risk_remaining = sum(1 for p in overflow_predictions if p.overflow_risk > 1.2)
            if high_risk_remaining > 0:
                print(f"   ⚠️  {high_risk_remaining} elementi potrebbero ancora richiedere controllo manuale")
            else:
                print(f"   ✅ Tutti i potenziali overflow sono stati gestiti")
        
        print(f"\n💡 Si consiglia di aprire il file tradotto in InDesign per verifica finale.")
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Operazione interrotta dall'utente")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Errore durante la traduzione: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
        
    finally:
        # Cleanup
        if 'processor' in locals():
            processor.close()

if __name__ == "__main__":
    main()