// Main Client-Side JS for Artisan Canvas Painting Platform

document.addEventListener('DOMContentLoaded', () => {
    // 1. Toast Notification Setup
    const toast = document.createElement('div');
    toast.className = 'toast-notification';
    toast.innerHTML = `<span class="toast-icon">✨</span> <span class="toast-text"></span>`;
    document.body.appendChild(toast);

    function showToast(message, isSuccess = true) {
        const toastText = toast.querySelector('.toast-text');
        toastText.textContent = message;
        toast.style.backgroundColor = isSuccess ? 'var(--deep-olive)' : '#a43a3a';
        toast.classList.add('show');
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3200);
    }

    // 2. AJAX Add-to-Cart Buttons
    document.querySelectorAll('.ajax-add-cart').forEach(button => {
        button.addEventListener('click', async (e) => {
            e.preventDefault();
            const paintingId = button.getAttribute('data-id');
            const originalText = button.innerHTML;

            try {
                button.innerHTML = '<span>Adding...</span>';
                button.disabled = true;

                const response = await fetch(`/cart/add/${paintingId}`, {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });

                const data = await response.json();

                if (data.success) {
                    showToast(data.message, true);
                    // Update navigation cart badges
                    document.querySelectorAll('.cart-badge').forEach(badge => {
                        badge.textContent = data.cart_count;
                    });
                    if (data.added) {
                        button.innerHTML = '<span>✓ In Cart</span>';
                        button.classList.add('in-cart');
                    } else {
                        button.innerHTML = originalText;
                    }
                } else {
                    showToast(data.message || 'Could not add to cart', false);
                    button.innerHTML = originalText;
                }
            } catch (err) {
                console.error('Error adding to cart:', err);
                showToast('Failed to add painting to cart.', false);
                button.innerHTML = originalText;
            } finally {
                button.disabled = false;
            }
        });
    });

    // 3. Live Image Preview for Add Painting Form
    const imageUrlInput = document.getElementById('image_url');
    const imageFileInput = document.getElementById('image_file');
    const previewImg = document.getElementById('previewImg');
    const previewPlaceholder = document.getElementById('previewPlaceholder');

    function updatePreview(src) {
        if (!previewImg) return;
        if (src) {
            previewImg.src = src;
            previewImg.style.display = 'block';
            if (previewPlaceholder) previewPlaceholder.style.display = 'none';
        } else {
            previewImg.src = '';
            previewImg.style.display = 'none';
            if (previewPlaceholder) previewPlaceholder.style.display = 'block';
        }
    }

    if (imageUrlInput) {
        imageUrlInput.addEventListener('input', () => {
            const url = imageUrlInput.value.trim();
            if (url) {
                updatePreview(url);
            }
        });
    }

    if (imageFileInput) {
        imageFileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (event) => {
                    updatePreview(event.target.result);
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // 4. Close flash alerts on click
    document.querySelectorAll('.flash-msg').forEach(msg => {
        msg.addEventListener('click', () => {
            msg.style.opacity = '0';
            setTimeout(() => msg.remove(), 300);
        });
    });
});
