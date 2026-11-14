use gizmo_nfs::{texture::{replace_images,Image},AssetHash};
use std::fs;
fn main()->Result<(),Box<dyn std::error::Error>>{
 let source=fs::read("CARS/COROLLA/TEXTURES.BIN")?;
 let black=vec![0u8;128*64*4];
 let (result,moved)=replace_images(&source,&[Image{hash:AssetHash(0x820f4c3a),rgba:&black,width:128,height:64}])?;
 assert!(!moved);assert_eq!(source.len(),result.len());
 fs::write("modding/staged-runtime/TEXTURES-no-neon.BIN",result)?;
 println!("Prepared zero-emission COROLLA_NEON in native pixel format; package not installed.");Ok(())
}
