"""
Example script demonstrating the BRS consolidation pipeline.
"""
from pathlib import Path
from app.services.orchestrator import BRSOrchestrator
from app.models.schemas import Priority, ApprovalStatus


def main():
    """Run example consolidation."""
    print("=" * 60)
    print("GenAI BRS Consolidator - Example Usage")
    print("=" * 60)
    
    # Initialize orchestrator
    print("\n1. Initializing orchestrator...")
    orchestrator = BRSOrchestrator()
    
    # Create sample data directory
    data_dir = Path("data/samples")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n2. Processing BRS documents...")
    print("   Note: Place your BRS PDF/DOCX files in data/samples/")
    
    # Example: Process multiple BRS versions
    brs_files = list(data_dir.glob("brs_*.pdf")) + list(data_dir.glob("brs_*.docx"))
    
    if not brs_files:
        print("   ⚠️  No BRS files found in data/samples/")
        print("   Please add BRS files named like: brs_v1.0.pdf, brs_v2.0.pdf")
    else:
        for idx, brs_file in enumerate(brs_files, 1):
            print(f"   Processing {brs_file.name}...")
            brs_doc = orchestrator.process_brs_document(
                file_path=brs_file,
                doc_id=f"BRS-2024-{idx:03d}",
                version=f"v{idx}.0"
            )
            print(f"   ✓ Processed: {brs_doc.metadata.doc_id} with {len(brs_doc.sections)} sections")
    
    print("\n3. Processing Change Requests...")
    cr_files = list(data_dir.glob("cr_*.pdf")) + list(data_dir.glob("cr_*.docx"))
    
    if not cr_files:
        print("   ⚠️  No CR files found in data/samples/")
        print("   Please add CR files named like: cr_001.pdf, cr_002.pdf")
    else:
        for idx, cr_file in enumerate(cr_files, 1):
            print(f"   Processing {cr_file.name}...")
            cr = orchestrator.process_change_request(
                file_path=cr_file,
                cr_id=f"CR-2024-{idx:03d}",
                priority=Priority.MEDIUM,
                approval_status=ApprovalStatus.APPROVED
            )
            print(f"   ✓ Processed: {cr.cr_id} with {len(cr.deltas)} deltas")
    
    # Check if we have data to consolidate
    stats = orchestrator.get_stats()
    print(f"\n4. Vector Store Statistics:")
    print(f"   - BRS Chunks: {stats['vector_store']['brs_chunks']}")
    print(f"   - CR Chunks: {stats['vector_store']['cr_chunks']}")
    
    if stats['vector_store']['total_chunks'] == 0:
        print("\n❌ No documents processed. Please add BRS and CR files to data/samples/")
        return
    
    print("\n5. Starting BRS Consolidation...")
    final_brs = orchestrator.consolidate_brs(
        brs_id="BRS-FINAL-2024-001",
        title="Consolidated Business Requirements Specification",
        version="v3.0"
    )
    
    print(f"\n6. Consolidation Results:")
    print(f"   - BRS ID: {final_brs.brs_id}")
    print(f"   - Version: {final_brs.version}")
    print(f"   - Sections: {len(final_brs.sections)}")
    print(f"   - Source BRS: {len(final_brs.source_brs_documents)}")
    print(f"   - Applied CRs: {len(final_brs.applied_change_requests)}")
    print(f"   - Validation: {'✅ PASSED' if final_brs.validation_passed else '❌ FAILED'}")
    
    if final_brs.validation_notes:
        print(f"\n   Validation Notes:")
        for note in final_brs.validation_notes[:5]:  # Show first 5
            print(f"   - {note}")
        if len(final_brs.validation_notes) > 5:
            print(f"   ... and {len(final_brs.validation_notes) - 5} more")
    
    print("\n7. Exporting Results...")
    output_dir = Path("data/outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    json_path = output_dir / f"{final_brs.brs_id}.json"
    md_path = output_dir / f"{final_brs.brs_id}.md"
    
    orchestrator.export_to_json(final_brs, json_path)
    orchestrator.export_to_markdown(final_brs, md_path)
    
    print(f"   ✓ JSON exported to: {json_path}")
    print(f"   ✓ Markdown exported to: {md_path}")
    
    print("\n" + "=" * 60)
    print("✅ Consolidation Complete!")
    print("=" * 60)
    print(f"\nNext steps:")
    print(f"1. Review the generated BRS at: {md_path}")
    print(f"2. Check validation notes if any issues were found")
    print(f"3. Use the JSON output for further processing")


if __name__ == "__main__":
    main()
