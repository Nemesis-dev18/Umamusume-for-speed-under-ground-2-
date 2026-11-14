//! Dry-run only: reads one admitted resource and emits rebuilt bytes to stdout, never writes game files.
use gizmo_nfs::{chunk::ChunkNode, geometry::{self,format::*,Mesh,Run},repack::Edits};
use std::{fs,io::{self,Write}};
fn solids(nodes:&[ChunkNode])->Vec<&ChunkNode>{let mut result=Vec::new();for node in nodes{if node.header.id==SOLID{result.push(node);}result.extend(solids(&node.children));}result}
fn u32at(bytes:&[u8],offset:usize)->u32{u32::from_le_bytes(bytes[offset..offset+4].try_into().unwrap())}
fn key(solid:&ChunkNode,bytes:&[u8])->u32{u32at(solid.find(SOLID_HEADER).unwrap().data(bytes),16)}
fn main()->Result<(),Box<dyn std::error::Error>>{
 let original=fs::read("CARS/COROLLA/GEOMETRY.BIN")?;
 let tree=ChunkNode::parse(&original)?;
 assert_eq!(geometry::rebuild(&original,&Edits::new())?,original,"no-op rebuild must be byte exact");
 let mut targets=Vec::new();
 for solid in solids(&tree){
  let (Some(vb),Some(mh))=(solid.find(VERTEX_BUFFER),solid.find(MESH_HEADER)) else{continue};
  let descriptor=geometry::skip_leading_filler(mh.data(&original));let count=u32at(descriptor,MESH_VERT_COUNT_FIELD*4)as usize;
  if count<3 || !geometry::standard_vertex_layout(count,vb.data(&original).len()){continue;}
  let vertices=&vb.data(&original)[vb.data(&original).len()-count*36..];
  if vertices.chunks_exact(36).all(|v|v[..12].chunks_exact(4).all(|f|f32::from_le_bytes(f.try_into().unwrap())==0.0)){
   targets.push(key(solid,&original));
  }
 }
 assert_eq!(targets.iter().collect::<std::collections::BTreeSet<_>>().len(),targets.len(),"part hashes must be unique");
 assert!(targets.len()>500,"expected collapsed prototype meshes, not a stock car");
 let mut result=original.clone();let pos=[[0.0f32;3];3];let normal=[[0.0f32,0.0,1.0];3];let uv=[[0.0f32;2];3];let color=[[255u8;4];3];let indices=[0,1,2];
 for (i,target) in targets.iter().enumerate(){
  let tree=ChunkNode::parse(&result)?;
  let solid=solids(&tree).into_iter().find(|s|key(s,&result)==*target).ok_or("lost solid")?;
  let ranges=solid.find(MATERIAL_RANGES).ok_or("no ranges")?;let count=ranges.data(&result).len()/MAT_RANGE_STRIDE;
  assert!(count>0);let mut runs=vec![Run{offset:3,count:0};count];runs[0]=Run{offset:0,count:3};
  result=geometry::replace_mesh(&result,solid.offset,&Mesh{positions:&pos,normals:&normal,colours:&color,uvs:&uv,indices:&indices,runs:Some(&runs)})?;
  if i%100==0{eprintln!("compacted {}/{} already collapsed solids in memory",i+1,targets.len());}
 }
 let tree=ChunkNode::parse(&result)?;let mut edits=Edits::new();
 for solid in solids(&tree){
  if !targets.contains(&key(solid,&result)){continue;}
  let header=solid.find(SOLID_HEADER).unwrap();let mut h=header.data(&result).to_vec();h[20..24].copy_from_slice(&1u32.to_le_bytes());edits.insert(header.offset,h);
  let ranges=solid.find(MATERIAL_RANGES).unwrap();let mut r=ranges.data(&result).to_vec();let count=r.len()/60;let lead=r.len()%60;
  for i in 0..count{for (at,value) in [(0,-0.01f32),(16,0.01f32)]{for axis in 0..3{let k=lead+i*60+at+axis*4;r[k..k+4].copy_from_slice(&value.to_le_bytes());}}}
  edits.insert(ranges.offset,r);
 }
 result=geometry::rebuild(&result,&edits)?;
 let tree=ChunkNode::parse(&result)?;let root=tree.iter().find(|n|n.header.id==0x80134000).ok_or("no root")?;
 let collision=tree.iter().find(|n|n.header.id==0x80034020).ok_or("no collision")?;
 let info=root.find(0x00134002).ok_or("no root info")?;let mut p=info.data(&result).to_vec();
 p[104..108].copy_from_slice(&(collision.offset as u32).to_le_bytes());p[108..112].copy_from_slice(&(collision.header.size+8).to_le_bytes());
 let mut edits=Edits::new();edits.insert(info.offset,p);result=geometry::rebuild(&result,&edits)?;
 let verified=ChunkNode::parse(&result)?;assert_eq!(solids(&tree).len(),solids(&verified).len());
 let back=gizmo_nfs::parse_geometry(&result)?;
 assert_eq!(back.len(),solids(&verified).len());
 for (mesh,solid) in back.iter().zip(solids(&verified)) {if targets.contains(&key(solid,&result)){assert_eq!(mesh.positions.len(),3);assert_eq!(mesh.indices.len(),3);assert!(mesh.positions.iter().all(|p|p.iter().all(|v|*v==0.0)));}}
 eprintln!("dry run complete: {} collapsed meshes; {} -> {} bytes; no resource written",targets.len(),original.len(),result.len());
 io::stdout().lock().write_all(&result)?;Ok(())
}
