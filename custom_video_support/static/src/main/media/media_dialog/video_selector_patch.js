import { VideoSelector } from "@html_editor/main/media/media_dialog/video_selector";
import { patch } from "@web/core/utils/patch";

patch(VideoSelector.prototype, {
    setup() {
        super.setup();
        this.PLATFORMS.vk = "vk";
        this.PLATFORMS.rutube = "rutube";
        
        if (this.OPTIONS.autoplay) {
            this.OPTIONS.autoplay.platforms.push("vk", "rutube");
        }        
    },

    async _getVideoURLData(url, options) {        
        const result = await super._getVideoURLData(url, options);        
        return result;
    }
});