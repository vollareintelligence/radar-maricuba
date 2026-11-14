import pathlib,re,base64,sys
S=pathlib.Path(__file__).resolve().parent.parent/'site'
h=(S/'index.html').read_text()
def b64(f,mime): return f"data:{mime};base64,"+base64.b64encode((S/f).read_bytes()).decode()
h=h.replace('<link rel="stylesheet" href="vendor/leaflet.css">','<style>'+(S/'vendor/leaflet.css').read_text()+'</style>')
h=h.replace('<script src="vendor/leaflet.js"></script>','<script>'+(S/'vendor/leaflet.js').read_text().replace('</script>','<\\/script>')+'</script>')
h=h.replace('<script src="dados.js"></script>','<script>'+(S/'dados.js').read_text().replace('</script>','<\\/script>')+'</script>')
h=re.sub(r'url\((["\']?)(fonts/[^)"\']+\.woff2)\1\)',lambda m:f"url({b64(m.group(2),'font/woff2')})",h)
h=re.sub(r'(["\'])(fotos/[^"\']+\.(jpg|jpeg|png|webp))\1',lambda m:m.group(1)+b64(m.group(2),'image/'+('jpeg' if m.group(3)=='jpg' else m.group(3)))+m.group(1),h)
out=S.parent/'dist/radar-maricuba.html'; out.parent.mkdir(exist_ok=True); out.write_text(h)
print(len(h)//1024,'KB; fotos/ restantes:',len(re.findall(r'fotos/',h)),'fonts/ restantes:',len(re.findall(r'fonts/',h)))
