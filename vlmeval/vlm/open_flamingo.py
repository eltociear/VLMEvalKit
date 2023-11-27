import torch
import requests
from PIL import Image
import os.path as osp

class OpenFlamingo: 

    INSTALL_REQ = True

    def __init__(self, 
                 name, 
                 with_context=False,
                 mpt_pth='/mnt/petrelfs/share_data/duanhaodong/mpt-7b/',
                 ckpt_pth='/mnt/petrelfs/share_data/duanhaodong/OpenFlamingo-9B-vitl-mpt7b/checkpoint.pt'):
        self.name = name
        assert name in ['v2']
        self.mpt_pth = mpt_pth
        try:
            from open_flamingo import create_model_and_transforms
        except:
            raise ImportError("Please first install open_flamingo to use OpenFlamingo")
        model, image_processor, tokenizer = create_model_and_transforms(
            clip_vision_encoder_path="ViT-L-14",
            clip_vision_encoder_pretrained="openai",
            lang_encoder_path=mpt_pth,
            tokenizer_path=mpt_pth,
            cross_attn_every_n_layers=4)
        ckpt = torch.load(ckpt_pth)
        model.load_state_dict(ckpt, strict=False)
        self.with_context = with_context
        torch.cuda.empty_cache()
        self.model = model.eval().cuda()
        self.tokenizer = tokenizer
        self.tokenizer.padding_side = "left"

        this_dir = osp.dirname(__file__)
    
        self.demo1 = Image.open(f"{this_dir}/misc/000000039769.jpg")
        self.demo2 = Image.open(f"{this_dir}/misc/000000028137.jpg")

        self.image_proc = image_processor
                
    def generate(self, image_path, prompt, dataset=None):
        if self.with_context:
            vision_x = [self.image_proc(x).unsqueeze(0) for x in [self.demo1, self.demo2, Image.open(image_path)]]
            vision_x = torch.cat(vision_x, dim=0)
        else:
            vision_x = self.image_proc(Image.open(image_path)).unsqueeze(0)
        vision_x = vision_x.unsqueeze(1).unsqueeze(0)
        if self.with_context:
            prompt = (
                "<image>Please describe the above image in a sentence. Answer: An image of two cats.<|endofchunk|>" +
                "<image>Please describe the above image in a sentence. Answer: An image of a bathroom sink.<|endofchunk|>" + 
                "<image>" + prompt + 'Answer: '
            )
        else:
            prompt = "<image>" + prompt + 'Answer: '
        lang_x = self.tokenizer([prompt], return_tensors="pt")
        generated_text = self.model.generate(
            vision_x=vision_x.cuda(), 
            lang_x=lang_x['input_ids'].cuda(), 
            attention_mask=lang_x['attention_mask'].cuda(), 
            max_new_tokens=256, 
            num_beams=3)
        generated_text = self.tokenizer.decode(generated_text[0])
        text = generated_text[len(prompt): ].split('<|endofchunk|>')[0]
        return text            