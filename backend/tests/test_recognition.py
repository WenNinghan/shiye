from pathlib import Path

import numpy as np
import pymupdf as fitz
import pytest

from shiye.recognition import (
    _prefer_latin_spacing,
    _restore_latin_spacing,
    ingest,
    parse_page_range,
    recognize_image,
)


def test_page_range():
    assert parse_page_range('1-3,5,2',5)==[0,1,2,4]
    for value in ['0','5-2','6','text','1-9999999']:
        with pytest.raises(ValueError):
            parse_page_range(value,5)


def test_native_pdf_extracts_text(settings,tmp_path):
    pdf=fitz.open()
    p=pdf.new_page()
    p.insert_text((40,60),'这是原生 PDF 中文文字无需重复识别',fontname='china-s',fontsize=18)
    data=pdf.tobytes()
    pages=ingest(data,'中文.pdf',tmp_path/'pages',settings)
    assert len(pages)==1 and pages[0].engine=='PDF 原生文字'
    assert '无需重复识别' in ''.join(b.text for b in pages[0].blocks)


def test_encrypted_pdf_rejected(settings,tmp_path):
    pdf=fitz.open()
    pdf.new_page()
    data=pdf.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256,owner_pw='owner',user_pw='password')
    with pytest.raises(ValueError,match='加密'):
        ingest(data,'locked.pdf',tmp_path/'pages',settings)


def test_spacing_candidate_may_only_add_whitespace():
    assert _prefer_latin_spacing(
        'FACULTYOFPOLITICALSCIENCE',
        'FACULTY OF POLITICAL SCIENCE',
        0.96,
    ) == 'FACULTY OF POLITICAL SCIENCE'
    assert _prefer_latin_spacing(
        'Nameoftheprogramme:InternationalRelations',
        'Name of the programme: International Relations',
        0.97,
    ) == 'Name of the programme: International Relations'
    assert _prefer_latin_spacing('Dr ukasz Gotota', 'Dr fukasz Ggtota', 0.99) == 'Dr ukasz Gotota'
    assert _prefer_latin_spacing('UNIVERSITYOFWARSAW', 'UNIVERSITY OF WARSAW', 0.80) == 'UNIVERSITYOFWARSAW'
    assert _prefer_latin_spacing('识别结果', '识别 结果', 0.99) == '识别结果'


def test_restore_latin_spacing_chooses_complete_safe_candidate():
    class FakeEngine:
        def text_rec(self, crops, use_cls):
            assert len(crops) == 8
            assert use_cls is False
            return [
                ('FACULTY OFPOLITICAL SCIENCE', 0.99),
                ('FACULTY OF POLITICAL SCIENCE', 0.96),
                ('FACULTY  OF POLITICAL SCIENCE', 0.94),
                ('FACULTY OF POUTICAL SCIENCE', 0.99),
                ('Dr fukasz Ggtota', 0.99),
                ('Dr ukasz Gotota', 0.99),
                ('Dr ukasz Gotota', 0.99),
                ('Dr ukasz Gotota', 0.99),
            ], 0.01

    rows = [
        [[[10, 10], [250, 10], [250, 30], [10, 30]], 'FACULTYOFPOLITICALSCIENCE', 0.99],
        [[[10, 40], [180, 40], [180, 60], [10, 60]], 'Dr ukasz Gotota', 0.98],
    ]
    repaired = _restore_latin_spacing(FakeEngine(), np.zeros((80, 280, 3), dtype=np.uint8), rows)
    assert repaired[0][1] == 'FACULTY OF POLITICAL SCIENCE'
    assert repaired[1][1] == 'Dr ukasz Gotota'
    assert rows[0][1] == 'FACULTYOFPOLITICALSCIENCE'


def test_real_chinese_ocr():
    sample=Path(__file__).resolve().parents[2]/'web/public/examples/notice.png'
    if not sample.exists():
        pytest.fail('先运行 scripts/make_samples.py 创建真实 OCR 样例')
    blocks,engine=recognize_image(str(sample))
    text='\n'.join(b['text'] for b in blocks)
    assert '项目' in text
    assert '2026' in text
    assert any(b['kind']=='table' and len(b['cells'])>=3 for b in blocks)
    assert engine.startswith('RapidOCR')
