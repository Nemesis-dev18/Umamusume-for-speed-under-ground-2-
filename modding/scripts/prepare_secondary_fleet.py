"""Stage independent garment rigs and bounded spring metadata; never install assets."""
import hashlib,json,math,re,struct
from pathlib import Path
import numpy as np
from pack_steam_fleet import ROOT,AXES,NativeSkin,pack


def category(name):
    return re.sub(r'\d+$','',name.split('_')[2])


def metadata(source,native,report):
    nodes=source.g['nodes'];paths={}
    for i in source.order:paths[i]=(paths[source.parents[i]]+'/' if i in source.parents else '')+nodes[i].get('name','')
    def find(name,part,shared=False):
        token={'body':'/pfb_bdy','head':'/pfb_chr','tail':'/pfb_tail'}[part]
        matches=[i for i,n in enumerate(nodes) if n.get('name')==name and token in '/'+paths[i] and (part!='body' or ('/pfb_chr' not in paths[i] and '/pfb_tail' not in paths[i]))]
        if not matches and shared and part!='body':return find(name,'body')
        if len(matches)!=1:raise ValueError(f'Ambiguous {part} attachment {name}: {matches}')
        return matches[0]
    chosen=[a for a in native['assets'] if a['logical'].endswith('_cloth00') and '_bust_' not in a['logical']]
    springs={};end_sim={};colliders=[];names={};unsupported=[]
    def add_collider(name,bone0,bone1,a,b,radius,kind):
        if not 0<radius<=2:raise ValueError('Collider radius outside local scale')
        index=len(colliders);colliders.append((bone0,bone1,kind,0,*a,*b,radius));names[name]=index;return index
    for asset in chosen:
        for chain in asset['chains']:
            root=next(n for n in asset['nodes'] if n['_boneName']==chain[0]);end_sim.update({name:bool(root.get('_needSimulateEndBone',0)) for name in chain})
        for n in asset['nodes']:
            if '_Bust' in n['_boneName'] or '_Ear' in n['_boneName']:continue
            i=find(n['_boneName'],asset['part']);springs[i]=(n,asset['part'])
        for c in asset['colliders']:
            if c['_type'] not in (0,2):unsupported.append({'name':c['_collisionName'],'type':c['_type']});continue
            if c['_radius']<=0:continue
            part='body' if c.get('_isOtherTarget') else asset['part'];i=find(c['_targetObjectName'],part,shared=True);ancestor=source.moving_parent(i)
            scale=float(np.linalg.norm(source.rest[i][:3,:3],axis=0).mean())
            def point(value):return AXES@(source.rest[i]@np.array([-value['x'],value['y'],value['z'],1.]))[:3]
            a=point(c['_offset']);b=point(c['_offset2']) if c['_type']==2 else a
            name=c['_collisionName']
            if name in names:raise ValueError('Duplicate native collider name')
            add_collider(name,source.remap[ancestor],source.remap[ancestor],a,b,c['_radius']*scale,(2 if c['_type']==2 else 0)|int(bool(c['_isInner'])))
    # Explicit body capsules supplement unsupported native collider variants.
    body_extra=[];leg_extra=[]
    def body_joint(name):
        i=find(name,'body');return source.remap[source.moving_parent(i)],AXES@source.rest[i][:3,3]
    hip,hp=body_joint('Hip');chest,cp=body_joint('Chest');body_extra.append(add_collider('RuntimeTorso',hip,chest,hp,cp,.14,2))
    for side in ('L','R'):
        knee_node=find('Knee_'+side,'body');thigh_node=source.parents[knee_node]
        thigh=source.remap[source.moving_parent(thigh_node)];tp=AXES@source.rest[thigh_node][:3,3];knee,kp=body_joint('Knee_'+side);ankle,ap=body_joint('Ankle_'+side)
        leg_extra.append(add_collider('RuntimeThigh_'+side,thigh,knee,tp,kp,.09,2));leg_extra.append(add_collider('RuntimeCalf_'+side,knee,ankle,kp,ap,.065,2))
    records=[];references=[];details=[]
    for i in source.bone_order:
        if i not in springs:continue
        n,part=springs[i];child=[j for j in nodes[i].get('children',[]) if j in springs]
        if child:tip=AXES@(source.rest[child[0]][:3,3]-source.rest[i][:3,3])
        elif end_sim[n['_boneName']]:
            parent=source.parents[i];tip=AXES@(source.rest[i][:3,3]-source.rest[parent][:3,3])
        else:continue
        length=float(np.linalg.norm(tip))
        if not .001<length<.6:raise ValueError(f'Invalid spring segment {n["_boneName"]}: {length}')
        stiffness=float(n['_stiffnessForce']);drag=float(n['_dragForce']);gravity=float(n['_gravity']);apply=float(n.get('MoveSpringApplyRate',1))
        if min(stiffness,drag,gravity)<0 or not 0<=apply<=1:raise ValueError('Invalid source spring coefficient')
        frequency=min(7.,2.+1.2*math.log1p(stiffness/100.));damping=min(1.2,max(.5,.45+.14*math.log1p(drag/100.)))
        angles=[abs(float(v)) for key in ['_limitAngleMin','_limitAngleMax'] for v in n[key].values()]
        cone=math.radians(min(75.,max(5.,max(angles)))) if n['_isLimit'] else math.radians(75.)
        wind=min(3.,max(0.,(float(n.get('_horizontalWindRateSlow',1))+float(n.get('_horizontalWindRateFast',1)))*.5))*.004
        refs=[names[name] for name in n['_collisionNameList'] if name in names]
        kind=category(n['_boneName'])
        # Native 180-degree axes are not usable as an isotropic cone for a linked garment.
        if kind=='Tail':
            cone=min(cone,math.radians(8.));frequency=2.2;damping=1.1;gravity*=.2;wind*=.2;apply*=.6
        elif kind=='Mantle' and native['id']==1062:
            cone=min(cone,math.radians(10.));frequency=max(frequency,4.);damping=max(damping,.95);wind*=.4
        if part=='body':refs+=body_extra
        if 'Skirt' in kind or kind in ('Jacket','Mantle'):refs+=leg_extra
        refs=list(dict.fromkeys(refs));first=len(references);references+=refs
        group=256 if kind=='Tail' else 0
        if kind=='Mantle' and native['id']==1062:
            group=1;ancestor=source.parents.get(i)
            while ancestor in springs and category(springs[ancestor][0]['_boneName'])=='Mantle':
                group+=1;ancestor=source.parents.get(ancestor)
            if group>16:raise ValueError('Cape synchronization depth budget')
        records.append((source.remap[i],group,first,len(refs),*tip,frequency,damping,9.81*min(2.,gravity/100.),float(n['_collisionRadius']),cone,wind,apply))
        details.append({'bone':source.remap[i],'name':n['_boneName'],'category':kind,'coherence_group':group&31,'tail_smoothing':bool(group&256),'tip_length':length,'native':{k:v for k,v in n.items() if k!='_childElements'},'adapted_hz':frequency,'damping_ratio':damping,'cone_degrees':math.degrees(cone),'wind_coefficient':wind,'colliders':[k for k,v in names.items() if v in refs]})
    nb=len(source.bone_order)
    if not records or len(records)>512 or len(colliders)>128 or len(references)>4096:raise ValueError('Secondary metadata budget')
    data=struct.pack('<4s5I',b'UMAS',1,nb,len(records),len(colliders),len(references))+b''.join(struct.pack('<4H10f',*r) for r in records)+b''.join(struct.pack('<4H7f',*c) for c in colliders)+struct.pack('<'+'H'*len(references),*references)
    data+=bytes((-len(data))%4)
    return data,{'joints':nb,'spring_nodes':details,'colliders':len(colliders),'unsupported_native_colliders':unsupported,'solver':'Bounded joint-tip spring approximation; native coefficients adapted to Hz/damping, not a claim of Unity solver equivalence','model_sha256':report['sha256']}


def main():
    inventory=json.loads((ROOT/'modding/uma-steam/secondary-native/structural-summary.json').read_text());rows=[]
    for c in json.loads((ROOT/'modding/fleet-source-inventory.json').read_text())['characters']:
        folder=ROOT/'modding/uma-steam/fleet'/str(c['id']);out=ROOT/'modding/staged-runtime/fleet-secondary'/str(c['id'])
        source,_,report=pack(folder,secondary=True,output=out)
        old=(folder/'runtime/model.umab').read_bytes();atlas=(folder/'runtime/model-atlas.umab').read_bytes();data=bytearray((out/'model.umab').read_bytes())
        nv,ni,nb=struct.unpack_from('<3I',data,8);ov,oi,ob=struct.unpack_from('<3I',old,8)
        if (nv,ni)!=(ov,oi) or data[40:40+nv*36]!=old[40:40+nv*36]:raise ValueError('Atlas reuse requires identical vertex order/rest data')
        at=40+nv*60+nb*16;ot=40+ov*60+ob*16
        if data[at:at+ni*2]!=old[ot:ot+ni*2]:raise ValueError('Index order changed')
        for v in range(nv):data[40+v*36+28:40+v*36+36]=atlas[40+v*36+28:40+v*36+36]
        data[at:at+ni*2]=atlas[ot:ot+ni*2];(out/'model-atlas.umab').write_bytes(data)
        (out/'atlas.dds').write_bytes((folder/'runtime/atlas.dds').read_bytes())
        physics,meta=metadata(source,next(x for x in inventory if x['id']==c['id']),report);(out/'secondary.bin').write_bytes(physics);(out/'secondary.json').write_text(json.dumps(meta,indent=2)+'\n')
        rows.append({'id':c['id'],'slot':c['nfs_slot'],'candidate_folder':str(out.relative_to(ROOT)),'bones':nb,'spring_nodes':len(meta['spring_nodes']),'sha256':{name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in ['model-atlas.umab','atlas.dds','secondary.bin']}})
        print(c['name'],'secondary nodes',len(meta['spring_nodes']),flush=True)
    (ROOT/'modding/secondary-fleet-plan.json').write_text(json.dumps({'characters':rows,'installed':False,'visual_reviewed':False,'gameplay_verified':False},indent=2)+'\n')

if __name__=='__main__':main()
