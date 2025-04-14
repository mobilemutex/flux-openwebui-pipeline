# User Guide

This guide provides detailed instructions for using the Open-WebUI integration with a local FLUX.1-dev model.

## Getting Started

After completing the installation process described in the [Installation Guide](./INSTALLATION.md), you can start generating images using the FLUX.1-dev model through Open-WebUI.

## Selecting the Flux Model

1. Open the Open-WebUI interface in your browser.
2. In the model selection dropdown (usually in the top-right corner), select "flux-generate".
3. You're now ready to generate images using your local FLUX.1-dev model.

## Basic Image Generation

To generate an image, simply enter a descriptive prompt in the chat interface:

```
Generate an image of a beautiful sunset over mountains
```

The system will:
1. Process your prompt
2. Send it to the Flux Server
3. Generate the image using your local FLUX.1-dev model
4. Display the generated image in the chat

## Using Custom Parameters

You can customize the image generation by including parameters in your prompt:

```
Generate an image of a beautiful sunset over mountains with parameters:
width: 1024
height: 768
steps: 50
guidance: 3.5
seed: 42
```

### Available Parameters

| Parameter | Description | Default | Recommended Range |
|-----------|-------------|---------|------------------|
| `width` | Image width in pixels | 1024 | 512-2048 |
| `height` | Image height in pixels | 1024 | 512-2048 |
| `steps` | Number of inference steps | 50 | 20-100 |
| `guidance` | Guidance scale (how closely to follow the prompt) | 3.5 | 2.0-7.0 |
| `seed` | Random seed for reproducibility | Random | Any integer |
| `negative_prompt` | Text description of what to avoid | None | Any text |

## Prompt Engineering Tips

The quality of your generated images depends significantly on the quality of your prompts. Here are some tips for writing effective prompts:

### Be Specific and Descriptive

Instead of:
```
Generate a mountain
```

Try:
```
Generate an image of a snow-capped mountain peak at sunrise with golden light illuminating the rocky cliffs, wispy clouds surrounding the summit, and a clear blue sky
```

### Specify Art Styles

Include specific art styles or artist references:
```
Generate an image of a futuristic cityscape with flying cars in the style of cyberpunk art, neon colors, detailed, 8k resolution
```

### Use Qualitative Adjectives

Include adjectives that describe quality:
```
Generate an image of a portrait of a young woman with photorealistic details, studio lighting, professional photography, high resolution, sharp focus
```

### Combine Subjects and Settings

Provide both a subject and a setting:
```
Generate an image of an astronaut riding a horse on Mars, red planet landscape, space helmet reflecting the surroundings, detailed spacesuit
```

### Specify Lighting and Atmosphere

Describe the lighting and atmosphere:
```
Generate an image of a forest path with dappled sunlight filtering through the leaves, morning mist, golden hour, atmospheric, serene mood
```

## Optimizing Parameters

### Resolution (Width and Height)

- Higher resolutions (e.g., 1024×1024 or 1536×1536) produce more detailed images but require more VRAM and processing time.
- For quick tests, use lower resolutions like 512×512.
- For final images, use higher resolutions.
- Consider aspect ratio based on your content:
  - Landscapes: wider aspect ratios (e.g., 1024×768)
  - Portraits: taller aspect ratios (e.g., 768×1024)
  - Balanced scenes: square aspect ratios (e.g., 1024×1024)

### Inference Steps

- More steps generally produce higher quality images but take longer to generate.
- 20-30 steps: Quick drafts with acceptable quality
- 50 steps: Good balance between quality and speed
- 75-100 steps: Highest quality, but diminishing returns after 50 steps

### Guidance Scale

- Controls how closely the model follows your prompt.
- Lower values (2.0-3.0): More creative/diverse results, but may not follow the prompt as closely
- Medium values (3.5-5.0): Good balance between creativity and prompt adherence
- Higher values (5.0-7.0): Strictly follows the prompt, but may produce less creative or more stereotypical images

### Seed

- Using the same seed with identical parameters will produce the same image.
- Useful for:
  - Reproducing previous results
  - Creating variations by keeping the seed but changing other parameters
  - A/B testing different prompts with the same composition

## Batch Generation

While the current integration doesn't directly support batch generation, you can achieve similar results by:

1. Using the same seed but varying other parameters
2. Submitting multiple prompts in sequence
3. Creating variations of a prompt with different artistic styles

## Saving Images

Images generated through Open-WebUI will appear in the chat interface. To save an image:

1. Right-click on the generated image
2. Select "Save image as..." from the context menu
3. Choose a location and filename for the image
4. Click "Save"

## Performance Considerations

### Memory Usage

The FLUX.1-dev model requires significant GPU memory, especially for larger image resolutions. To optimize memory usage:

- Use lower resolutions for drafts
- Reduce the batch size (currently fixed at 1)
- Enable model CPU offloading in the server configuration
- Close other GPU-intensive applications

### Generation Speed

Image generation time depends on several factors:

- Image resolution (higher = slower)
- Number of inference steps (more = slower)
- GPU performance
- Server load

For faster generation:
- Use fewer inference steps (20-30)
- Use smaller resolutions
- Ensure the GPU is not being used by other applications

## Troubleshooting

### Image Generation Issues

If your generated images have issues:

- **Blurry or low-quality images**: Increase the number of steps, use a higher resolution, or improve your prompt with more details
- **Images don't match your prompt**: Increase the guidance scale, make your prompt more specific, or remove conflicting descriptions
- **Generation fails**: Check server logs, reduce resolution, or ensure your GPU has enough memory
- **Slow generation**: Reduce resolution, use fewer steps, or check for other processes using the GPU

### Connection Issues

If Open-WebUI can't connect to the Flux Server:

- Verify the server is running: `curl http://your-server-ip:8000/api/health`
- Check the `FLUX_SERVER_URL` environment variable
- Ensure network connectivity between Open-WebUI and the server
- Check for firewall rules blocking the connection

## Advanced Usage

### Combining with Other Models

You can use the Flux image generation alongside text models in Open-WebUI:

1. Start a conversation with a text model
2. Ask it to help you craft a prompt for image generation
3. Switch to the "flux-generate" model
4. Use the crafted prompt to generate an image
5. Switch back to the text model to discuss the generated image

### Iterative Refinement

For best results, use an iterative approach:

1. Start with a basic prompt and generate an image
2. Analyze the result and identify aspects to improve
3. Refine your prompt with more specific details
4. Generate a new image with the refined prompt
5. Repeat until satisfied with the result

## Getting Help

If you encounter issues not covered in this guide:

1. Check the server logs for error messages
2. Verify your configuration
3. Run the test scripts to diagnose issues
4. Refer to the [Troubleshooting](./README.md#troubleshooting) section in the main documentation
5. Open an issue on the GitHub repository with detailed information about your problem
