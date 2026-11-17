//! Stage only two named shadow textures for one admitted character slot.
use gizmo_nfs::{texture::{replace_images,Image,Tpk},AssetHash};
use std::{fs,io::{self,Write}};
fn hash(s:&str)->u32{s.bytes().fold(u32::MAX,|h,c|h.wrapping_mul(33).wrapping_add(c as u32))}
fn main()->Result<(),Box<dyn std::error::Error>>{
 let slot=std::env::args().nth(1).ok_or("expected slot")?;
 if !["COROLLA","240SX","MIATA","FOCUS","PEUGOT","PEUGOT106","CORSA"].contains(&slot.as_str()){return Err("unapproved slot".into());}
 let source=fs::read(format!("CARS/{slot}/TEXTURES.BIN"))?;let rgba=fs::read("modding/staged-runtime/fleet-shadows/compact-foot-shadow.rgba")?;if rgba.len()!=128*64*4{return Err("invalid shadow image size".into());}
 let targets=[hash(&format!("{slot}_SHADOWFE")),hash(&format!("{slot}_SHADOWIG"))];let directory=Tpk::directory(&source)?;
 for key in targets{if directory.iter().filter(|e|e.hash==AssetHash(key)).count()!=1{return Err("shadow absent/ambiguous".into());}}
 let images=[Image{hash:AssetHash(targets[0]),rgba:&rgba,width:128,height:64},Image{hash:AssetHash(targets[1]),rgba:&rgba,width:128,height:64}];let (out,moved)=replace_images(&source,&images)?;
 for entry in Tpk::directory(&out)?{if targets.contains(&entry.hash.0){let decoded=Tpk::decode_one(&out,&entry)?;assert_eq!((decoded.width,decoded.height),(128,64));}}
 eprintln!("{slot}: two compact shadows staged; relocation={moved}");io::stdout().lock().write_all(&out)?;Ok(())
}
