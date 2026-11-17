// Rasterize only when displayed text changes. Reapply indexed glyph pixels on
// every presentation so moving terrain never erases the HUD or leaves trails.
struct TextRun {
 int x,y;std::wstring text;
 bool operator==(const TextRun& other)const{return x==other.x&&y==other.y&&text==other.text;}
};
struct TextPixel {uint16_t x,y;uint8_t color;};
struct TextMask {
 int width,height;uint32_t builds=0;std::vector<TextRun> cached;
 std::vector<TextPixel> pixels;
 TextMask(int w,int h):width(w),height(h){}
 bool update(const std::vector<TextRun>& runs){
#ifndef MYTH_TEXT_NO_CACHE
  if(builds&&cached==runs)return true;
#endif
  HDC dc=CreateCompatibleDC(nullptr);if(!dc)return false;
  BITMAPINFO info{};info.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);info.bmiHeader.biWidth=width;info.bmiHeader.biHeight=-height;info.bmiHeader.biPlanes=1;info.bmiHeader.biBitCount=32;void* bits=nullptr;
  HBITMAP bitmap=CreateDIBSection(dc,&info,DIB_RGB_COLORS,&bits,nullptr,0);if(!bitmap){DeleteDC(dc);return false;}
  auto old=SelectObject(dc,bitmap);auto raster=(uint32_t*)bits;std::fill(raster,raster+width*height,0x00ff00ff);
  static HFONT font=CreateFontW(-14,0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,HANGEUL_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,NONANTIALIASED_QUALITY,DEFAULT_PITCH,L"굴림");auto oldFont=font?SelectObject(dc,font):nullptr;SetBkMode(dc,TRANSPARENT);
  for(const auto& run:runs){int n=(int)run.text.size();SetTextColor(dc,RGB(0,0,0));TextOutW(dc,run.x+1,run.y+1,run.text.c_str(),n);SetTextColor(dc,RGB(255,255,255));TextOutW(dc,run.x,run.y,run.text.c_str(),n);}
  GdiFlush();pixels.clear();
  for(int y=0;y<height;++y)for(int x=0;x<width;++x){uint32_t value=raster[y*width+x]&0xffffff;if(value!=0xff00ff)pixels.push_back({(uint16_t)x,(uint16_t)y,(uint8_t)(value?255:0)});}
  if(oldFont)SelectObject(dc,oldFont);SelectObject(dc,old);DeleteObject(bitmap);DeleteDC(dc);
  cached=runs;++builds;return true;
 }
 void paint(uint8_t* target,int pitch,int left,int top)const{for(const auto& pixel:pixels)target[(top+pixel.y)*pitch+left+pixel.x]=pixel.color;}
};
TextMask resourceMask(430,148),timerMask(150,20);
