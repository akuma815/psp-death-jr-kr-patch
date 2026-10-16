"""Rebuild current translation from original media, retaining verified movie assets."""
import hashlib
import json
import runpy
from pathlib import Path
import build_korean as text
import build_movie_iso_007 as movie

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / 'build/008_updated_translation_kyobo24'

def main(output_dir=None, iso_name='DeathJr_KR_008_UpdatedTranslation_Kyobo24.iso'):
    global B
    if output_dir is not None: B=Path(output_dir).resolve()
    assert not B.exists(), 'Existing build is preserved'
    source_hash = text.poc.digest(text.CSV)
    # Both stages are products of this invocation, not previous patched releases.
    staging = ROOT / 'work/temp' / (B.name + '_text_build')
    assert not staging.exists(), 'Existing staging directory is preserved'
    text.main(staging, 'text_stage.iso')
    runpy.run_path(str(ROOT / 'scripts/test_korean_runtime.py'), run_name='__main__')
    text_iso = staging / 'text_stage.iso'
    movie.main(base_path=text_iso, expected_base_hash=text.poc.digest(text_iso),
               output_dir=B, iso_name=iso_name,
               reuse_pmf=ROOT / 'workspace/video/verified_pmf_007')
    assert text.poc.digest(text.CSV) == source_hash, 'Translation changed during build'
    # Keep text-stage provenance and CPU evidence next to the final product.
    for name in ('build_report.json', 'mips_runtime_verification.json', 'insertion_plan.json', 'font_mapping.json'):
        (B / ('text_' + name)).write_bytes((staging / name).read_bytes())
    report = json.loads((B / 'build_report.json').read_text(encoding='utf-8'))
    report.update(build=B.name, csv_sha256=source_hash,
                  text_build_report='text_build_report.json',
                  cpu_verification='text_mips_runtime_verification.json', runtime='NOT RUN')
    (B / 'build_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

if __name__ == '__main__':
    main()
