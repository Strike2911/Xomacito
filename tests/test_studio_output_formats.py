import base64
import os
import shutil
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree

import pytest
from PIL import Image

from src.core.image_converter import ImageConverter
from tests.test_image_studio_workflow import make


@pytest.mark.parametrize('format', ['PNG', 'JPG', 'WEBP', 'AVIF', 'TIFF', 'ICO', 'ICNS', 'BMP', 'SVG', 'PDF'])
def test_studio_output_is_a_real_readable_file(tmp_path, format):
    source = tmp_path / 'portrait.png'
    Image.new('RGBA', (64, 96), (210, 20, 100, 180)).save(source)
    target = tmp_path / ('converted.' + format.lower())
    converter = ImageConverter()
    assert converter.convert_file(str(source), str(target), {'format': format})
    assert target.stat().st_size > 0
    if format == 'SVG':
        root = ElementTree.parse(target).getroot()
        assert root.attrib['viewBox'] == '0 0 64 96'
        image = root.find('{http://www.w3.org/2000/svg}image')
        href = image.attrib['{http://www.w3.org/1999/xlink}href']
        with Image.open(BytesIO(base64.b64decode(href.split(',', 1)[1]))) as embedded:
            assert embedded.size == (64, 96)
            assert embedded.mode == 'RGBA'
    elif format == 'PDF':
        from pdf2image import convert_from_path
        root = Path(__file__).resolve().parents[1]
        name = 'pdftoppm.exe' if os.name == 'nt' else 'pdftoppm'
        binary = next((root / "bin" / "poppler").rglob(name), None)
        if binary is None:
            installed = shutil.which(name)
            if not installed:
                pytest.skip('PDF rendering requires Poppler')
            binary = Path(installed)
        pages = convert_from_path(str(target), poppler_path=str(binary.parent), first_page=1, last_page=1)
        assert len(pages) == 1 and pages[0].width > 0
    else:
        with Image.open(target) as result:
            result.load()
            assert result.format == ('JPEG' if format == 'JPG' else format)
            if format == 'ICNS':
                assert result.size == (1024, 1024)
                assert result.convert('RGBA').getpixel((0, 0))[3] == 0


def test_keep_format_matches_extension_and_preserves_dimensions(tmp_path):
    controller = make(tmp_path)
    source = tmp_path / 'original.jpg'
    Image.new('RGB', (80, 40), 'blue').save(source)
    item = dict(path=str(source), title='copy', pages=1, page=1)
    target = controller._output_path(tmp_path, item, 'No Convertir')
    assert target.suffix == '.jpg'
    assert ImageConverter().convert_file(str(source), str(target), {'format': 'No Convertir'})
    with Image.open(target) as result:
        assert result.format == 'JPEG'
        assert result.size == (80, 40)
    item['path'] = str(tmp_path / 'document.pdf')
    assert controller._output_path(tmp_path, item, 'No Convertir').suffix == '.png'


def test_visible_ai_controls_reach_processing_options(tmp_path):
    controller = make(tmp_path)
    for key, value in dict(rembgGpu=False, rembgSmooth=4, rembgExpand=-2,
                           upscaleTile='128', upscaleTta=True, upscaleScale='4').items():
        controller.setOption(key, value)
    options = controller._conversion_options()
    assert options['rembg_gpu'] is False
    assert options['rembg_edge_smooth'] == 4
    assert options['rembg_edge_expand'] == -2
    assert options['upscale_tile'] == '128'
    assert options['upscale_tta'] is True
    assert options['upscale_scale'] == '4'
