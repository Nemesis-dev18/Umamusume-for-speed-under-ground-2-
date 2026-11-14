use gizmo_nfs::{chunk::ChunkNode,geometry::{self,format::*,Mesh,Run},repack::Edits,texture::{Tpk,replace_images,Image},AssetHash};
use std::fs;
fn u32at(b:&[u8],at:usize)->u32{u32::from_le_bytes(b[at..at+4].try_into().unwrap())}
fn solids(nodes:&[ChunkNode])->Vec<&ChunkNode>{let mut all=Vec::new();for n in nodes{if n.header.id==SOLID{all.push(n);}all.extend(solids(&n.children));}all}
fn body_name(n:&ChunkNode,b:&[u8])->String{geometry::part_name(n.find(SOLID_HEADER).unwrap().data(b))}
fn main()->Result<(),Box<dyn std::error::Error>>{
 let mut out=fs::read("CARS/COROLLA/GEOMETRY.BIN")?;let tree=ChunkNode::parse(&out)?;
 let names:Vec<_>=solids(&tree).into_iter().map(|s|body_name(s,&out)).filter(|n|n.contains("_KIT00_BODY_")).collect();assert_eq!(names.len(),4);
 let pos=[[0.,0.,0.],[0.,0.25,0.],[0.,0.5,0.],[0.,0.,0.],[0.,0.,1.],[0.,0.,2.]];let normal=[[1.,0.,0.];6];let colors=[[255u8;4];6];let mut uv=[[0f32;2];6];for i in 0..6{uv[i]=[0.17320508+i as f32*0.03125,0.31415927+i as f32*0.03125];}let indices=[0,1,2,3,4,5];
 for name in &names{
  let tree=ChunkNode::parse(&out)?;let solid=solids(&tree).into_iter().find(|s|body_name(s,&out)==*name).unwrap();let ranges=solid.find(MATERIAL_RANGES).unwrap().data(&out);let shaders=solid.find(MATERIAL_SHADERS).unwrap().data(&out);let n=ranges.len()/60;let lead=ranges.len()%60;
  let active:Vec<_>=(0..n).filter(|i|u32at(shaders,u32at(ranges,lead+i*60+32)as usize*8)==0xd6d6080a).collect();assert_eq!(active.len(),1);let active=active[0];let mut runs=Vec::new();for i in 0..n{runs.push(Run{offset:if i<=active{0}else{6},count:if i==active{6}else{0}});}
  out=geometry::replace_mesh(&out,solid.offset,&Mesh{positions:&pos,normals:&normal,colours:&colors,uvs:&uv,indices:&indices,runs:Some(&runs)})?;
 }
 let bounds=fs::read("modding/staged-runtime/motion-bounds.bin")?;assert_eq!(bounds.len(),24);let tree=ChunkNode::parse(&out)?;let mut edits=Edits::new();
 for solid in solids(&tree){if !names.contains(&body_name(solid,&out)){continue;}let header=solid.find(SOLID_HEADER).unwrap();let mut h=header.data(&out).to_vec();h[20..24].copy_from_slice(&2u32.to_le_bytes());h[32..44].copy_from_slice(&bounds[..12]);h[48..60].copy_from_slice(&bounds[12..]);edits.insert(header.offset,h);
  let ranges=solid.find(MATERIAL_RANGES).unwrap();let mut r=ranges.data(&out).to_vec();let lead=r.len()%60;for at in (lead..r.len()).step_by(60){if u32at(&r,at+12)>0{r[at..at+12].copy_from_slice(&bounds[..12]);r[at+16..at+28].copy_from_slice(&bounds[12..]);}}edits.insert(ranges.offset,r);
 }
 out=geometry::rebuild(&out,&edits)?;let tree=ChunkNode::parse(&out)?;let root=tree.iter().find(|n|n.header.id==0x80134000).unwrap();let collision=tree.iter().find(|n|n.header.id==0x80034020).unwrap();let info=root.find(0x00134002).unwrap();let mut data=info.data(&out).to_vec();data[104..108].copy_from_slice(&(collision.offset as u32).to_le_bytes());data[108..112].copy_from_slice(&(collision.header.size+8).to_le_bytes());let mut edits=Edits::new();edits.insert(info.offset,data);out=geometry::rebuild(&out,&edits)?;
 let back=gizmo_nfs::parse_geometry(&out)?;for name in &names{let p=back.iter().find(|p|p.name==*name).unwrap();assert_eq!(p.positions.len(),6);assert_eq!(p.indices.len(),6);}
 fs::write("modding/staged-runtime/GEOMETRY-proxy.BIN",out)?;
 let textures=fs::read("CARS/COROLLA/TEXTURES.BIN")?;let rgba=fs::read("modding/staged-runtime/foot-shadow.rgba")?;assert_eq!(rgba.len(),128*64*4);
 let images=[Image{hash:AssetHash(0xb7f6575b),rgba:&rgba,width:128,height:64},Image{hash:AssetHash(0xb7f657c0),rgba:&rgba,width:128,height:64}];let (result,moved)=replace_images(&textures,&images)?;
 for e in Tpk::directory(&result)?{if images.iter().any(|i|i.hash==e.hash){let t=Tpk::decode_one(&result,&e)?;assert_eq!((t.width,t.height),(128,64));}}
 fs::write("modding/staged-runtime/TEXTURES-shadow.BIN",result)?;println!("Prepared four six-vertex carriers and two original-format footprint shadows; texture relocation={moved}; no installed game resources changed.");Ok(())
}
