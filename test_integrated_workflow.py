#!/usr/bin/env python3
"""
Test integrato del workflow completo con modalità diagrammi
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from overflow_detector import OverflowDetector, TextFrameMetrics
from overflow_manager import OverflowManager
import json

def test_integrated_diagram_workflow():
    """Test workflow completo per gestione diagrammi"""
    
    print("🔄 Test Workflow Integrato - Modalità Diagrammi")
    print("=" * 60)
    
    # === FASE 1: SETUP COMPONENTI ===
    detector = OverflowDetector()
    manager = OverflowManager()
    
    # === FASE 2: SIMULA DATI DOCUMENTO ===
    # Frame diagramma complesso con overflow critico
    critical_diagram = TextFrameMetrics(
        frame_id="flowchart_main",
        width=250.0,
        height=200.0,
        x=100.0,
        y=100.0,
        column_count=1,
        column_gutter=12.0,
        inset_spacing=(2.0, 2.0, 2.0, 2.0),
        font_size=8.5,
        leading=10.2,
        char_count=320,  # Molto testo in spazio ristretto
        estimated_overflow_risk=1.8  # Overflow critico
    )
    
    # Frame procedura con rischio alto
    procedure_frame = TextFrameMetrics(
        frame_id="procedure_steps",
        width=300.0,
        height=180.0,
        x=150.0,
        y=150.0,
        column_count=1,
        column_gutter=12.0,
        inset_spacing=(3.0, 3.0, 3.0, 3.0),
        font_size=9.0,
        leading=10.8,
        char_count=280,
        estimated_overflow_risk=1.5  # Overflow alto
    )
    
    # Frame testo normale (controllo)
    normal_frame = TextFrameMetrics(
        frame_id="normal_text",
        width=400.0,
        height=300.0,
        x=50.0,
        y=50.0,
        column_count=1,
        column_gutter=12.0,
        inset_spacing=(6.0, 6.0, 6.0, 6.0),
        font_size=12.0,
        leading=14.4,
        char_count=200,
        estimated_overflow_risk=0.7  # Normale
    )
    
    frame_metrics = {
        "flowchart_main": critical_diagram,
        "procedure_steps": procedure_frame,
        "normal_text": normal_frame
    }
    
    # === FASE 3: SIMULA CONTENUTO STORIES ===
    from xml.etree import ElementTree as ET
    
    # Story con contenuto flowchart tipico
    flowchart_story_xml = """
    <Story>
        <ParagraphStyleRange>
            <CharacterStyleRange>
                <Content>Überprüfung der Systemkomponenten durchführen</Content>
                <Content>Sind alle Bauteile in ordnungsgemäßem Zustand?</Content>
                <Content>Ja → Weiter zu Funktionalitätsprüfung</Content>
                <Content>Nein → Beschädigte Komponenten ersetzen und neue Zertifizierung</Content>
                <Content>Dokumentation verfügbar machen</Content>
                <Content>Ist die Installation korrekt ausgeführt?</Content>
                <Content>Visuelle Inspektion der beweglichen Teile</Content>
            </CharacterStyleRange>
        </ParagraphStyleRange>
    </Story>
    """
    
    # Story con procedura operativa
    procedure_story_xml = """
    <Story>
        <ParagraphStyleRange>
            <CharacterStyleRange>
                <Content>Schritt für Schritt Anleitung zur Wartung</Content>
                <Content>Erste Phase: Vorbereitung der Arbeitsumgebung</Content>
                <Content>Zweite Phase: Systematische Überprüfung aller Elemente</Content>
                <Content>Dritte Phase: Durchführung der Messtechnischen Prüfung</Content>
                <Content>Abschließende Dokumentation und Freigabe</Content>
            </CharacterStyleRange>
        </ParagraphStyleRange>
    </Story>
    """
    
    # Story testo normale
    normal_story_xml = """
    <Story>
        <ParagraphStyleRange>
            <CharacterStyleRange>
                <Content>Questo manuale contiene le istruzioni per l'installazione del sistema SafeGuard.</Content>
                <Content>Si prega di leggere attentamente tutte le sezioni prima di procedere.</Content>
            </CharacterStyleRange>
        </ParagraphStyleRange>
    </Story>
    """
    
    stories_data = {
        "Story_flowchart": {"root": ET.fromstring(flowchart_story_xml)},
        "Story_procedure": {"root": ET.fromstring(procedure_story_xml)},
        "Story_normal": {"root": ET.fromstring(normal_story_xml)}
    }
    
    print(f"📊 Setup test data:")
    print(f"   - {len(frame_metrics)} frame con diversi livelli di rischio")
    print(f"   - {len(stories_data)} stories con contenuti specializzati")
    
    # === FASE 4: RILEVAMENTO DIAGRAMMI ===
    print(f"\n🎯 Rilevamento automatico diagrammi...")
    diagram_frames = detector.detect_diagram_frames(frame_metrics, stories_data)
    
    print(f"   ✅ Rilevati {len(diagram_frames)} frame diagramma")
    
    for frame_id, info in diagram_frames.items():
        risk_level = info['compression_priority']
        diagram_score = info['diagram_score']
        print(f"   📊 {frame_id}: score={diagram_score:.2f}, priorità={risk_level}")
    
    # === FASE 5: PREDIZIONE OVERFLOW ===
    print(f"\n🔍 Predizione overflow per traduzione tedesca...")
    
    test_texts = [
        "Überprüfung der Systemkomponenten durchführen - sind alle Bauteile in ordnungsgemäßem Zustand?",
        "Schritt für Schritt Anleitung zur systematischen Wartung aller beweglichen Teile",
        "Questo manuale contiene le istruzioni per l'installazione del sistema."
    ]
    
    overflow_predictions = detector.predict_translation_overflow(
        test_texts, 'de', frame_metrics
    )
    
    high_risk_count = sum(1 for p in overflow_predictions if p.overflow_risk > 1.2)
    print(f"   ⚠️  {high_risk_count}/{len(overflow_predictions)} testi ad alto rischio overflow")
    
    # === FASE 6: COMPRESSIONE SPECIALIZZATA ===
    print(f"\n🔧 Applicazione compressione specializzata...")
    
    # Test compressione diagrammi
    if diagram_frames:
        processed_texts = manager.process_diagram_frames(diagram_frames, test_texts)
        
        total_original = sum(len(text) for text in test_texts)
        total_compressed = sum(len(text) for text in processed_texts)
        compression_ratio = (total_original - total_compressed) / total_original * 100
        
        print(f"   📉 Compressione totale: {compression_ratio:.1f}%")
        print(f"   💾 Caratteri risparmiati: {total_original - total_compressed}")
        
        for i, (orig, comp) in enumerate(zip(test_texts, processed_texts)):
            if len(comp) < len(orig):
                saving = len(orig) - len(comp)
                print(f"   ✂️  Testo {i+1}: -{saving} char ({saving/len(orig)*100:.1f}%)")
    
    # === FASE 7: RISOLUZIONE OVERFLOW STANDARD ===
    print(f"\n🛠️  Risoluzione overflow con strategie multiple...")
    
    if overflow_predictions:
        resolutions = manager.resolve_overflow_predictions(overflow_predictions)
        
        successful = sum(1 for r in resolutions if r.success)
        total_saved = sum(r.space_saved for r in resolutions)
        
        print(f"   ✅ {successful}/{len(resolutions)} risoluzioni riuscite")
        print(f"   💾 Spazio totale risparmiato: {total_saved} caratteri")
        
        # Mostra dettagli strategie utilizzate
        methods_used = {}
        for resolution in resolutions:
            if resolution.resolution_method != 'no_action_needed':
                methods = resolution.resolution_method.split('+')
                for method in methods:
                    methods_used[method] = methods_used.get(method, 0) + 1
        
        if methods_used:
            print(f"   📊 Strategie utilizzate:")
            for method, count in sorted(methods_used.items(), key=lambda x: x[1], reverse=True):
                print(f"      - {method}: {count} volte")
    
    # === FASE 8: SUGGERIMENTI LAYOUT ===
    print(f"\n🎨 Generazione suggerimenti layout dinamici...")
    
    layout_suggestions_count = 0
    for frame_id, metrics in frame_metrics.items():
        # Trova overflow risk per questo frame
        frame_overflow_risk = next(
            (p.overflow_risk for p in overflow_predictions if p.frame_id == metrics.frame_id), 
            metrics.estimated_overflow_risk
        )
        
        suggestions = manager.get_layout_suggestions(metrics, frame_overflow_risk)
        if suggestions:
            layout_suggestions_count += len(suggestions)
            
            if frame_overflow_risk > 1.2:  # Mostra solo per frame critici
                print(f"   🔧 {frame_id} ({len(suggestions)} suggerimenti):")
                for suggestion in suggestions[:2]:  # Prime 2 per non sovraccaricare
                    print(f"      - {suggestion['action']}: {suggestion['expected_benefit']}")
    
    print(f"   💡 Generati {layout_suggestions_count} suggerimenti di layout totali")
    
    # === FASE 9: REPORT COMPLETO ===
    print(f"\n📊 Generazione report completi...")
    
    # Report rilevamento diagrammi
    detection_report = detector.generate_diagram_detection_report(diagram_frames)
    
    # Report compressione
    if overflow_predictions and resolutions:
        compression_report = manager.generate_compression_report(resolutions)
    else:
        compression_report = {"summary": {"total_texts": 0}}
    
    # Report grafiche
    graphics_report = manager.generate_graphics_report(diagram_frames, overflow_predictions)
    
    # === FASE 10: RISULTATI FINALI ===
    print(f"\n🎉 RISULTATI WORKFLOW INTEGRATO")
    print(f"=" * 40)
    
    print(f"📊 Rilevamento:")
    print(f"   - Diagrammi identificati: {len(diagram_frames)}")
    print(f"   - Frame critici: {detection_report['summary'].get('critical_frames_count', 0)}")
    print(f"   - Score medio diagrammi: {detection_report['summary'].get('average_diagram_score', 0):.2f}")
    
    print(f"🔧 Compressione:")
    print(f"   - Testi processati: {compression_report['summary']['total_texts']}")
    print(f"   - Tasso successo: {compression_report['summary'].get('success_rate', 0)}%")
    print(f"   - Spazio risparmiato: {compression_report['summary'].get('total_space_saved', 0)} char")
    
    print(f"🎨 Layout:")
    print(f"   - Suggerimenti generati: {layout_suggestions_count}")
    print(f"   - Frame con overflow: {high_risk_count}")
    
    print(f"📈 Grafiche:")
    if graphics_report['status'] == 'graphics_detected':
        print(f"   - Elementi grafici: {graphics_report['summary']['total_graphics']}")
        print(f"   - Rischio complessivo: {graphics_report['summary']['overall_risk']:.2f}")
        print(f"   - Impatto traduzione: {graphics_report['translation_impact']['overall_overflow_risk']:.2f}")
    else:
        print(f"   - Nessun elemento grafico problematico")
    
    # === SALVATAGGIO REPORT ===
    print(f"\n💾 Salvataggio report integrato...")
    
    integrated_report = {
        'workflow_summary': {
            'diagram_frames_detected': len(diagram_frames),
            'overflow_predictions': len(overflow_predictions),
            'high_risk_frames': high_risk_count,
            'layout_suggestions': layout_suggestions_count,
            'compression_applied': successful if 'successful' in locals() else 0,
            'total_space_saved': total_saved if 'total_saved' in locals() else 0
        },
        'detection_report': detection_report,
        'compression_report': compression_report,
        'graphics_report': graphics_report,
        'test_data': {
            'frame_count': len(frame_metrics),
            'story_count': len(stories_data),
            'test_texts_count': len(test_texts)
        }
    }
    
    report_file = "integrated_workflow_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(integrated_report, f, indent=2, ensure_ascii=False)
    
    print(f"   📁 Report salvato: {report_file}")
    
    # === RACCOMANDAZIONI FINALI ===
    print(f"\n💡 RACCOMANDAZIONI WORKFLOW:")
    
    if len(diagram_frames) > 0:
        print(f"   🎯 Modalità diagrammi RACCOMANDATA per questo documento")
        
        if detection_report['summary'].get('critical_frames_count', 0) > 0:
            print(f"   🚨 Revisione manuale necessaria per frame critici")
        
        print(f"   📋 Strategie consigliate:")
        for rec in graphics_report.get('recommendations', {}).get('flowcharts', [])[:2]:
            print(f"      - {rec}")
    
    if high_risk_count > len(frame_metrics) * 0.3:
        print(f"   ⚠️  Alto numero di frame a rischio - considerare pre-processing")
    
    if layout_suggestions_count > 10:
        print(f"   🎨 Molti suggerimenti layout - documento complesso")
    
    print(f"\n✅ Test workflow integrato completato!")
    
    return integrated_report

if __name__ == "__main__":
    try:
        report = test_integrated_diagram_workflow()
        
        print(f"\n🎊 Test completato con successo!")
        
        # Analisi finale
        workflow_summary = report['workflow_summary']
        
        if workflow_summary['diagram_frames_detected'] > 0:
            print(f"✨ Sistema diagrammi: {workflow_summary['diagram_frames_detected']} frame processati")
        
        if workflow_summary['compression_applied'] > 0:
            print(f"💪 Compressione: {workflow_summary['total_space_saved']} caratteri risparmiati")
        
        if workflow_summary['layout_suggestions'] > 0:
            print(f"🎨 Layout: {workflow_summary['layout_suggestions']} ottimizzazioni proposte")
        
        print(f"\n🚀 Sistema pronto per elaborazione documenti IDML con diagrammi!")
        
    except Exception as e:
        print(f"\n❌ Errore durante il test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)