using System;
using System.IO;
namespace oMPSComposer {
class Entry {
static int Main(string[] args) {
if(args.Length!=3) throw new Exception("input.264 input.rawatx output.mps");
if(File.Exists(args[2])) throw new Exception("Output exists");
byte[] data=File.ReadAllBytes(args[1]);
if(data[0]!=15 || data[1]!=208) throw new Exception("Bad AU header");
int packet=(((data[2]&3)<<8)|(data[3]*8))+16;
byte[] header=new byte[8];Array.Copy(data,header,8);
if(data.Length%packet!=0) throw new Exception("Incomplete audio");
for(int p=0;p<data.Length;p+=packet) for(int j=0;j<8;j++) if(data[p+j]!=header[j]) throw new Exception("AU mismatch");
var atrac=new AtracReader(data,packet-8,44100,header);
MpsMuxer.Mux(args[0],atrac,args[2]);return 0;
}}}
