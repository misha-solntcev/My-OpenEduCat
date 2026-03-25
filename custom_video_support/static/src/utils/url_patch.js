/** @odoo-module **/
import { EmbeddedVideoComponent } from "@html_editor/others/embedded_components/core/video/video";
import { patch } from "@web/core/utils/patch";

patch(EmbeddedVideoComponent.prototype, {
    setup() {
        if (this.props.platform === 'rutube' || this.props.platform === 'vk') {
            let urlStr = "";
            if (this.props.platform === 'rutube') {
                urlStr = `https://rutube.ru/play/embed/${this.props.videoId}`;
            } else {
                const parts = this.props.videoId.split('_');
                // parts[0] = oid, parts[1] = id
                urlStr = `https://vk.com/video_ext.php?oid=${parts[0]}&id=${parts[1]}`;
                // parts[2] = hash (добавляем только если он есть и не пустой)
                if (parts.length > 2 && parts[2]) {
                    urlStr += `&hash=${parts[2]}`;
                }
            }

            const url = new URL(urlStr);
            if (this.props.params) {
                Object.entries(this.props.params).forEach(([k, v]) => {
                    if (k !== 'hash') url.searchParams.set(k, v);
                });
            }
            this.src = url.toString();
            return;
        }
        super.setup();
    }
});
