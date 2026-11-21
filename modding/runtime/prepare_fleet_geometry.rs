//! Read one admitted car and emit a compact carrier container; never install game data.
use gizmo_nfs::{chunk::ChunkNode,geometry::{self,format::*,Mesh,Run},repack::Edits};
use std::{fs,io::{self,Write}};
fn u32at(b:&[u8],at:usize)->u32{u32::from_le_bytes(b[at..at+4].try_into().unwrap())}
fn f32at(b:&[u8],at:usize)->f32{f32::from_le_bytes(b[at..at+4].try_into().unwrap())}
fn solids(nodes:&[ChunkNode])->Vec<&ChunkNode>{let mut all=Vec::new();for n in nodes{if n.header.id==SOLID{all.push(n);}all.extend(solids(&n.children));}all}
fn key(n:&ChunkNode,b:&[u8])->u32{u32at(n.find(SOLID_HEADER).unwrap().data(b),16)}
fn main()->Result<(),Box<dyn std::error::Error>>{
 let args:Vec<_>=std::env::args().collect();if args.len()!=3{return Err("expected slot and character ID".into());}
 let slot=&args[1];let id:u32=args[2].parse()?;let admitted=[("COROLLA",1068),("240SX",1052),("MIATA",1032),("FOCUS",1062),("PEUGOT",1015),("PEUGOT106",1006),("CORSA",1058),("350Z",9001),("CELICA",1067),("LANCEREVO8",1067)];
 if !admitted.iter().any(|(name,number)|*name==slot && *number==id){return Err("unapproved slot/character pair".into());}
 let original=fs::read(format!("CARS/{slot}/GEOMETRY.BIN"))?;let raw=fs::read(format!("modding/staged-runtime/fleet/{id}/carrier.bin"))?;let bounds=fs::read(format!("modding/staged-runtime/fleet/{id}/bounds.bin"))?;
 if raw.len()!=216 || bounds.len()!=24{return Err("carrier/bounds length".into());}
 let mut pos=[[0f32;3];6];let mut normals=[[0f32;3];6];let mut uv=[[0f32;2];6];let colors=[[255u8;4];6];
 for v in 0..6{for k in 0..3{pos[v][k]=f32at(&raw,v*36+k*4);normals[v][k]=f32at(&raw,v*36+12+k*4);}for k in 0..2{uv[v][k]=f32at(&raw,v*36+28+k*4);}}
 for at in (0..24).step_by(4){if !f32at(&bounds,at).is_finite(){return Err("nonfinite bounds".into());}}
 let tree=ChunkNode::parse(&original)?;assert_eq!(geometry::rebuild(&original,&Edits::new())?,original);
 let targets:Vec<_>=solids(&tree).iter().map(|s|key(s,&original)).collect();assert_eq!(targets.iter().collect::<std::collections::BTreeSet<_>>().len(),targets.len());
 let mut out=original;let hidden_pos=[[0f32;3];3];let hidden_normals=[[1f32,0.,0.];3];let hidden_uv=[[0f32;2];3];let hidden_colors=[[255u8;4];3];let mut bodies=0;
 for (index,target) in targets.iter().enumerate(){
  let tree=ChunkNode::parse(&out)?;let solid=solids(&tree).into_iter().find(|s|key(s,&out)==*target).ok_or("lost solid")?;let name=geometry::part_name(solid.find(SOLID_HEADER).unwrap().data(&out));let body=name.contains("_BODY_");
  let ranges=solid.find(MATERIAL_RANGES).ok_or("missing material ranges")?.data(&out);let count=ranges.len()/60;let lead=ranges.len()%60;let mut runs=vec![Run{offset:0,count:0};count];
  if body{
   let shaders=solid.find(MATERIAL_SHADERS).ok_or("missing shaders")?.data(&out);let active=(0..count).find(|i|u32at(shaders,u32at(ranges,lead+i*60+32)as usize*8)==0xd6d6080a).ok_or("no carpaint carrier material")?;
   for i in 0..count{runs[i]=Run{offset:if i<=active{0}else{6},count:if i==active{6}else{0}};}bodies+=1;
  }else{if runs.is_empty(){return Err("hidden part without material range".into());}for i in 0..count{runs[i]=Run{offset:if i==0{0}else{3},count:if i==0{3}else{0}};}}
  let indices=[0u32,1,2,3,4,5];let hidden_indices=[0u32,1,2];let mesh=if body{Mesh{positions:&pos,normals:&normals,colours:&colors,uvs:&uv,indices:&indices,runs:Some(&runs)}}else{Mesh{positions:&hidden_pos,normals:&hidden_normals,colours:&hidden_colors,uvs:&hidden_uv,indices:&hidden_indices,runs:Some(&runs)}};
  out=geometry::replace_mesh(&out,solid.offset,&mesh).map_err(|e|format!("{name}: {e}"))?;
  if index%100==0{eprintln!("{slot}: compacted {}/{} solids",index+1,targets.len());}
 }
 if bodies!=20{return Err("expected all five kits and four LODs".into());}
 let tree=ChunkNode::parse(&out)?;let mut edits=Edits::new();
 for solid in solids(&tree){
  let node=solid.find(SOLID_HEADER).unwrap();let mut header=node.data(&out).to_vec();let body=geometry::part_name(&header).contains("_BODY_");header[20..24].copy_from_slice(&(if body{2u32}else{1}).to_le_bytes());
  if body{header[32..44].copy_from_slice(&bounds[..12]);header[48..60].copy_from_slice(&bounds[12..]);for r in 0..4{for c in 0..4{header[64+(r*4+c)*4..68+(r*4+c)*4].copy_from_slice(&(if r==c{1f32}else{0.}).to_le_bytes());}}}
  edits.insert(node.offset,header);
  if body{let ranges=solid.find(MATERIAL_RANGES).unwrap();let mut data=ranges.data(&out).to_vec();let lead=data.len()%60;for at in (lead..data.len()).step_by(60){data[at..at+12].copy_from_slice(&bounds[..12]);data[at+16..at+28].copy_from_slice(&bounds[12..]);}edits.insert(ranges.offset,data);}
 }
 out=geometry::rebuild(&out,&edits)?;let tree=ChunkNode::parse(&out)?;let root=tree.iter().find(|n|n.header.id==0x80134000).ok_or("SolidList absent")?;let collision=tree.iter().find(|n|n.header.id==0x80034020).ok_or("collision absent")?;let info=root.find(0x00134002).ok_or("SolidList info absent")?;let mut data=info.data(&out).to_vec();data[104..108].copy_from_slice(&(collision.offset as u32).to_le_bytes());data[108..112].copy_from_slice(&(collision.header.size+8).to_le_bytes());let mut edits=Edits::new();edits.insert(info.offset,data);out=geometry::rebuild(&out,&edits)?;
 let back=ChunkNode::parse(&out)?;assert_eq!(solids(&back).len(),targets.len());for solid in solids(&back){let body=geometry::part_name(solid.find(SOLID_HEADER).unwrap().data(&out)).contains("_BODY_");let vb=solid.find(VERTEX_BUFFER).unwrap().data(&out);if body{assert!(vb.ends_with(&raw));}}
 eprintln!("{slot}: {bodies} carriers; {} bytes; no resource installed",out.len());io::stdout().lock().write_all(&out)?;Ok(())
}
